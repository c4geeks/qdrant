#!/usr/bin/env python3
"""Tune the background optimizer and write-ahead log.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

for name in ("tuned", "wal_tuned"):
    if client.collection_exists(name):
        client.delete_collection(name)

# Optimizer config — controls background merges + HNSW index build trigger
client.create_collection(
    collection_name="tuned",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    optimizers_config=models.OptimizersConfigDiff(
        default_segment_number=4,
        indexing_threshold=20000,
        memmap_threshold=200000,
        max_optimization_threads=2,
    ),
)

# WAL config — durability layer for upserts/deletes
client.create_collection(
    collection_name="wal_tuned",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    wal_config=models.WalConfigDiff(
        wal_capacity_mb=64,
        wal_segments_ahead=2,
    ),
)

for n in ("tuned", "wal_tuned"):
    info = client.get_collection(n)
    print(f"--- {n} ---")
    print(f"  optimizer: {info.config.optimizer_config}")
    print(f"  wal:       {info.config.wal_config}")
