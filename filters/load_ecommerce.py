"""Load a 100k synthetic e-commerce dataset into Qdrant.

Each product has:
- dense vector: 384-dim MiniLM embedding of the product description
- sparse vector: BM25 over the same description
- payload: brand (keyword), category (keyword w/ is_tenant), price (float),
           in_stock (bool), rating (float), created_at (datetime), description (text),
           location (lon, lat) geo
"""
from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding, TextEmbedding


URL = "http://localhost:6333"
COLLECTION = "products"
N = 100_000
BATCH = 500            # well under the 32 MiB REST limit
DENSE_DIM = 384

CATEGORIES = [
    "Laptops", "Phones", "Headphones", "Cameras", "Watches",
    "Bikes", "Tents", "Boots", "Backpacks", "Cookware",
    "Books", "Toys", "Skincare", "Coffee", "Wine",
]
BRANDS = [
    "Acme", "Northwind", "Globex", "Initech", "Umbrella",
    "Soylent", "Cyberdyne", "Stark", "Wayne", "Wonka",
    "Hooli", "Wayland", "Massive", "Aperture", "Vehement",
]
# 15 cities, lon/lat order (Qdrant convention)
CITIES = [
    (-0.1276,  51.5072, "London"),
    (  2.3522, 48.8566, "Paris"),
    ( 13.4050, 52.5200, "Berlin"),
    (-74.0060, 40.7128, "New York"),
    (-87.6298, 41.8781, "Chicago"),
    (-122.4194,37.7749, "San Francisco"),
    (-118.2437,34.0522, "Los Angeles"),
    ( 139.6917,35.6895, "Tokyo"),
    ( 100.5018,13.7563, "Bangkok"),
    (  37.6173,55.7558, "Moscow"),
    ( 151.2093,-33.8688,"Sydney"),
    (  18.4241,-33.9249,"Cape Town"),
    (  31.2357,30.0444, "Cairo"),
    (  77.2090,28.6139, "Delhi"),
    ( 116.4074,39.9042, "Beijing"),
]


def make_description(rng: random.Random, idx: int) -> tuple[str, str, str]:
    cat = rng.choice(CATEGORIES)
    brand = rng.choice(BRANDS)
    adjectives = ["lightweight", "rugged", "premium", "compact", "wireless",
                  "waterproof", "ergonomic", "professional", "ultra-fast",
                  "all-weather", "noise-cancelling", "fast-charging"]
    adj = rng.choice(adjectives)
    color = rng.choice(["black", "silver", "white", "blue", "red", "green"])
    desc = (
        f"{brand} {adj} {cat[:-1].lower()} model #{idx} in {color}. "
        f"Designed for daily use with long battery life and modern materials. "
        f"Recommended for travel, work, and outdoor adventures."
    )
    return cat, brand, desc


def main() -> None:
    client = QdrantClient(url=URL, timeout=120)

    print("Loading embedding models (first run downloads weights to ~/.cache/fastembed)...")
    t0 = time.time()
    dense_model = TextEmbedding("BAAI/bge-small-en-v1.5")          # 384-dim
    sparse_model = SparseTextEmbedding("Qdrant/bm25")               # BM25 sparse
    print(f"  loaded in {time.time() - t0:.1f}s")

    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)

    # Create collection with one named dense + one sparse vector
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False),
                modifier=models.Modifier.IDF,
            ),
        },
    )
    print(f"Created collection '{COLLECTION}' (dense=384 Cosine + sparse=BM25/IDF)")

    rng = random.Random(2026)
    now = datetime.now(timezone.utc)

    total_emb = 0.0
    total_upsert = 0.0
    start = time.time()
    for start_idx in range(0, N, BATCH):
        end_idx = min(start_idx + BATCH, N)
        descs = []
        meta = []
        for i in range(start_idx, end_idx):
            cat, brand, desc = make_description(rng, i)
            lon, lat, _ = rng.choice(CITIES)
            # tiny jitter so points aren't exactly on the city marker
            lon += rng.uniform(-0.5, 0.5)
            lat += rng.uniform(-0.5, 0.5)
            descs.append(desc)
            meta.append({
                "brand": brand,
                "category": cat,
                "price": round(rng.uniform(5, 1500), 2),
                "in_stock": rng.random() > 0.15,
                "rating": round(rng.uniform(1.0, 5.0), 1),
                "created_at": (now - timedelta(days=rng.randint(0, 730))).isoformat(),
                "description": desc,
                "location": {"lon": lon, "lat": lat},
            })

        t1 = time.time()
        dense_vecs = list(dense_model.embed(descs, batch_size=128))
        sparse_vecs = list(sparse_model.embed(descs, batch_size=128))
        total_emb += time.time() - t1

        points = []
        for j, (dv, sv, m) in enumerate(zip(dense_vecs, sparse_vecs, meta)):
            points.append(
                models.PointStruct(
                    id=start_idx + j,
                    vector={
                        "dense": dv.tolist(),
                        "bm25": models.SparseVector(
                            indices=sv.indices.tolist(),
                            values=sv.values.tolist(),
                        ),
                    },
                    payload=m,
                )
            )

        t2 = time.time()
        client.upsert(collection_name=COLLECTION, points=points, wait=False)
        total_upsert += time.time() - t2

        if start_idx % 5000 == 0:
            elapsed = time.time() - start
            rate = (start_idx + len(points)) / max(elapsed, 0.001)
            print(f"  loaded {end_idx:>6}/{N} "
                  f"({rate:.0f} pts/s, emb={total_emb:.1f}s upsert={total_upsert:.1f}s)")

    # Wait for indexing
    print("waiting for indexing to settle...")
    time.sleep(10)
    info = client.get_collection(COLLECTION)
    print()
    print(f"Final status:       {info.status}")
    print(f"Points:             {info.points_count}")
    print(f"Indexed vectors:    {info.indexed_vectors_count}")
    print(f"Segments:           {info.segments_count}")
    print(f"Total wall time:    {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
