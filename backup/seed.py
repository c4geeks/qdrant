"""Seed two real collections so the snapshot/restore demos are non-trivial."""
import random, time
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

URL = "http://localhost:6333"
client = QdrantClient(url=URL, timeout=60)

dense = TextEmbedding("BAAI/bge-small-en-v1.5")
print("Model loaded")

# Collection 1: articles (1,000 real BGE-small embeddings)
if client.collection_exists("articles"):
    client.delete_collection("articles")
client.create_collection(
    "articles",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
)

random.seed(2026)
topics = ["kubernetes", "postgres", "nginx", "redis", "kafka", "docker",
          "terraform", "ansible", "vector search", "embeddings", "rag",
          "openai", "llama", "fastapi", "prometheus", "grafana"]
adjectives = ["complete", "quick", "advanced", "production", "real-world",
              "self-hosted", "scalable", "secure", "lightweight", "resilient"]
verbs = ["install", "configure", "deploy", "monitor", "scale", "secure",
         "back up", "migrate", "tune", "audit"]

descs = []
for i in range(1000):
    t = random.choice(topics)
    a = random.choice(adjectives)
    v = random.choice(verbs)
    descs.append(f"A {a} guide to {v} {t} for production. Real commands, real output, real benchmarks. {i}")

t0 = time.time()
vectors = list(dense.embed(descs, batch_size=64))
print(f"Embedded 1000 in {time.time() - t0:.1f}s")

points = []
for i, (v, d) in enumerate(zip(vectors, descs)):
    points.append(models.PointStruct(
        id=i, vector=v.tolist(),
        payload={"title": d, "topic": d.split()[3], "rank": i % 100},
    ))
for start in range(0, len(points), 500):
    client.upsert("articles", points=points[start:start+500], wait=True)

# Collection 2: products (200 synthetic embeddings, 8-dim, small to keep snapshot quick)
if client.collection_exists("products"):
    client.delete_collection("products")
client.create_collection(
    "products",
    vectors_config=models.VectorParams(size=8, distance=models.Distance.DOT),
)
rng = random.Random(7)
prod_points = [
    models.PointStruct(
        id=i,
        vector=[rng.random() for _ in range(8)],
        payload={"sku": f"P-{i:05d}", "price": round(rng.uniform(5, 500), 2)},
    )
    for i in range(200)
]
client.upsert("products", points=prod_points, wait=True)

print()
print("Final state:")
for c in client.get_collections().collections:
    info = client.get_collection(c.name)
    print(f"  {c.name:<10} points={info.points_count:>4}  vectors={info.indexed_vectors_count}")
