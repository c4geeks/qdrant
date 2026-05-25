#!/usr/bin/env python3
"""Multi-tenancy via the tenant payload index. One collection serves
many tenants; storage is physically partitioned by the tenant key.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

if client.collection_exists("tenants"):
    client.delete_collection("tenants")

client.create_collection(
    collection_name="tenants",
    vectors_config=models.VectorParams(
        size=384, distance=models.Distance.COSINE,
    ),
)

# The critical flag: is_tenant=True. Qdrant partitions storage by this key.
client.create_payload_index(
    "tenants",
    field_name="tenant_id",
    field_schema=models.KeywordIndexParams(
        type="keyword",
        is_tenant=True,
    ),
)

# Search MUST always include the tenant filter or it ranges across tenants
def search_for_tenant(tenant_id: str, query_vec):
    return client.query_points(
        collection_name="tenants",
        query=query_vec,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
            ],
        ),
        limit=10,
    )

info = client.get_collection("tenants")
schema = info.payload_schema.get("tenant_id")
print(f"tenant_id  data_type={schema.data_type}  is_tenant={getattr(schema.params, 'is_tenant', None)}")
