"""Seed two collections + drive a sustained query load for Grafana to plot."""
import asyncio
import os
import random
import time
from qdrant_client import AsyncQdrantClient, QdrantClient, models
from fastembed import TextEmbedding

URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
KEY = "CHANGE_ME_TO_A_STRONG_KEY"

def seed():
    client = QdrantClient(url=URL, api_key=KEY, timeout=120)
    if client.collection_exists("articles"):
        client.delete_collection("articles")
    client.create_collection(
        "articles",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        shard_number=6, replication_factor=2, write_consistency_factor=2,
    )
    if client.collection_exists("products"):
        client.delete_collection("products")
    client.create_collection(
        "products",
        vectors_config=models.VectorParams(size=8, distance=models.Distance.DOT),
        shard_number=2, replication_factor=2,
    )

    dense = TextEmbedding("BAAI/bge-small-en-v1.5")
    random.seed(7)
    descs = [f"A guide to {random.choice(['install','configure','tune'])} "
             f"{random.choice(['nginx','postgres','redis','kafka','kubernetes'])} #{i}"
             for i in range(5000)]
    t0 = time.time()
    vecs = list(dense.embed(descs, batch_size=64))
    print(f"Embedded {len(vecs)} in {time.time()-t0:.1f}s")

    pts = [models.PointStruct(id=i, vector=v.tolist(),
                              payload={"title": d, "rank": i%100})
           for i, (v, d) in enumerate(zip(vecs, descs))]
    t0 = time.time()
    for s in range(0, len(pts), 500):
        client.upsert("articles", points=pts[s:s+500], wait=True)
    print(f"Upsert articles in {time.time()-t0:.1f}s")

    rng = random.Random(0)
    ppts = [models.PointStruct(id=i, vector=[rng.random() for _ in range(8)],
                               payload={"sku": f"P-{i:05d}"})
            for i in range(2000)]
    client.upsert("products", points=ppts, wait=True)
    print("Seeded products (2000 dot-8d)")
    client.close()
    return vecs

async def drive_load(query_vec, seconds=600):
    client = AsyncQdrantClient(url=URL, api_key=KEY)
    start = time.time()
    count = 0
    last_report = start
    while time.time() - start < seconds:
        # Mix: 80% query, 20% scroll/count
        tasks = []
        for _ in range(10):
            r = random.random()
            if r < 0.8:
                tasks.append(client.query_points("articles", query=query_vec, limit=5))
            elif r < 0.95:
                tasks.append(client.scroll("articles", limit=5, with_payload=False))
            else:
                tasks.append(client.count("articles", exact=False))
        await asyncio.gather(*tasks, return_exceptions=True)
        count += 10
        now = time.time()
        if now - last_report > 10:
            rps = count / (now - start)
            print(f"  t={int(now-start)}s  total={count}  rps={rps:.1f}")
            last_report = now
        await asyncio.sleep(0.05)
    await client.close()
    print(f"Load loop ended: {count} ops in {seconds}s")

if __name__ == "__main__":
    vecs = seed()
    print("Driving 10 minutes of load...")
    asyncio.run(drive_load(vecs[0].tolist(), seconds=600))
