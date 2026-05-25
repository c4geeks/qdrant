#!/usr/bin/env python3
"""Create a basic Qdrant collection with one dense vector space.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("basic_docs"):
    client.delete_collection("basic_docs")

client.create_collection(
    collection_name="basic_docs",
    vectors_config=models.VectorParams(
        size=384,                          # match your embedding model
        distance=models.Distance.COSINE,   # COSINE, DOT, EUCLID, or MANHATTAN
    ),
)

info = client.get_collection("basic_docs")
print(f"status={info.status}  segments={info.segments_count}")
print(f"size={info.config.params.vectors.size}  distance={info.config.params.vectors.distance}")
