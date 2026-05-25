#!/usr/bin/env python3
"""Create payload indexes for all 7 supported schema types.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("payload_indexed"):
    client.delete_collection("payload_indexed")

client.create_collection(
    collection_name="payload_indexed",
    vectors_config=models.VectorParams(size=64, distance=models.Distance.COSINE),
)

# Simple schemas — keyword / integer / float / bool / geo / datetime
simple = {
    "category":     models.PayloadSchemaType.KEYWORD,
    "view_count":   models.PayloadSchemaType.INTEGER,
    "rating":       models.PayloadSchemaType.FLOAT,
    "is_published": models.PayloadSchemaType.BOOL,
    "location":     models.PayloadSchemaType.GEO,
    "published_at": models.PayloadSchemaType.DATETIME,
}
for field, kind in simple.items():
    client.create_payload_index(
        "payload_indexed", field_name=field, field_schema=kind,
    )

# Text index — needs explicit tokenizer params
client.create_payload_index(
    "payload_indexed",
    field_name="body",
    field_schema=models.TextIndexParams(
        type="text",
        tokenizer=models.TokenizerType.WORD,
        min_token_len=2,
        max_token_len=20,
        lowercase=True,
    ),
)

info = client.get_collection("payload_indexed")
print(f"indexed payload fields ({len(info.payload_schema)}):")
for k, v in info.payload_schema.items():
    print(f"  {k:14s} -> {v.data_type}")
