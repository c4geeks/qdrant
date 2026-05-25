#!/usr/bin/env python3
"""Create a memory-frugal collection where vectors, payload, and HNSW
graph all live on disk. Best for billion-point collections on hosts
with limited RAM.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("on_disk_collection"):
    client.delete_collection("on_disk_collection")

client.create_collection(
    collection_name="on_disk_collection",
    vectors_config=models.VectorParams(
        size=1536,                          # OpenAI text-embedding-3-small
        distance=models.Distance.COSINE,
        on_disk=True,                       # raw vectors memory-mapped
    ),
    on_disk_payload=True,                   # payload bytes on disk too
    hnsw_config=models.HnswConfigDiff(
        on_disk=True,                       # HNSW graph lifted off heap
    ),
)

info = client.get_collection("on_disk_collection")
print(f"vector.on_disk    = {info.config.params.vectors.on_disk}")
print(f"on_disk_payload   = {info.config.params.on_disk_payload}")
print(f"hnsw.on_disk      = {info.config.hnsw_config.on_disk}")
