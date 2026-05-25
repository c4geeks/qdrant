#!/usr/bin/env python3
"""Create a collection that mixes dense and sparse vectors.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("sparse_demo"):
    client.delete_collection("sparse_demo")

client.create_collection(
    collection_name="sparse_demo",
    vectors_config={
        "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse_idx": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
        ),
    },
)

client.upsert(
    collection_name="sparse_demo",
    points=[
        models.PointStruct(
            id=1,
            vector={
                "dense": [0.1] * 384,
                "sparse_idx": models.SparseVector(
                    indices=[42, 1024, 5000],
                    values=[0.7, 0.3, 0.9],
                ),
            },
            payload={"title": "Rust vector database"},
        ),
    ],
)

info = client.get_collection("sparse_demo")
print(f"dense  = {info.config.params.vectors['dense'].size}-dim cosine")
print(f"sparse = {list(info.config.params.sparse_vectors.keys())}")
print(f"points = {info.points_count}")
