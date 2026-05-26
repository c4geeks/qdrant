"""Create a sharded + replicated collection and probe distribution."""
import random
import time
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

URL = "http://localhost:6333"
KEY = "CHANGE_ME_TO_A_STRONG_KEY"

client = QdrantClient(url=URL, api_key=KEY, timeout=120)

dense = TextEmbedding("BAAI/bge-small-en-v1.5")
print("Model loaded")

if client.collection_exists("articles"):
    client.delete_collection("articles")

# 6 shards * 2 replicas = 12 shard-replicas across 3 nodes = 4 per node
client.create_collection(
    "articles",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    shard_number=6,
    replication_factor=2,
    write_consistency_factor=2,   # majority write
)
print("Created collection: shard_number=6, replication_factor=2, write_consistency=2")

random.seed(2026)
topics = ["kubernetes", "postgres", "nginx", "redis", "kafka", "docker",
          "terraform", "ansible", "vector search", "embeddings", "rag",
          "fastapi", "prometheus", "grafana"]
verbs = ["install", "configure", "deploy", "monitor", "scale", "secure"]
descs = [f"A guide to {random.choice(verbs)} {random.choice(topics)} for production. #{i}"
         for i in range(5000)]

t0 = time.time()
vectors = list(dense.embed(descs, batch_size=64))
print(f"Embedded 5000 in {time.time() - t0:.1f}s")

points = [
    models.PointStruct(id=i, vector=v.tolist(), payload={"title": d, "topic": d.split()[3]})
    for i, (v, d) in enumerate(zip(vectors, descs))
]
t0 = time.time()
for start in range(0, len(points), 500):
    client.upsert("articles", points=points[start:start+500], wait=True)
print(f"Upsert 5000 in {time.time() - t0:.1f}s with write_consistency=2")

# Verify count
info = client.get_collection("articles")
print(f"Final: points={info.points_count}, status={info.status}")
print(f"Cluster shard distribution:")
shards = client.http.cluster_api.collection_cluster_info(collection_name="articles")
print(f"  local: {len(shards.result.local_shards)} shards")
print(f"  remote: {len(shards.result.remote_shards)} shards")
for s in shards.result.local_shards:
    print(f"    LOCAL shard_id={s.shard_id} state={s.state} points={s.points_count}")
for s in shards.result.remote_shards[:6]:
    print(f"    REMOTE shard_id={s.shard_id} peer_id={s.peer_id} state={s.state}")
