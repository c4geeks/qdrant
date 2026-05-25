#!/usr/bin/env python3
"""Create one collection with multiple named vector spaces (text + image).

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("named_vectors"):
    client.delete_collection("named_vectors")

client.create_collection(
    collection_name="named_vectors",
    vectors_config={
        "text":  models.VectorParams(size=384, distance=models.Distance.COSINE),
        "image": models.VectorParams(size=512, distance=models.Distance.COSINE),
    },
)

# Upsert one point with both vectors and a payload
client.upsert(
    collection_name="named_vectors",
    points=[
        models.PointStruct(
            id=1,
            vector={
                "text":  [0.1] * 384,
                "image": [0.2] * 512,
            },
            payload={"sku": "ABC-123"},
        ),
    ],
)

# Search using the named vector via the `using` parameter
results = client.query_points(
    collection_name="named_vectors",
    query=[0.1] * 384,
    using="text",
    limit=5,
)
for p in results.points:
    print(f"  id={p.id} score={p.score:.4f}  payload={p.payload}")
