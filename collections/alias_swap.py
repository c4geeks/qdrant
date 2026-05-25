#!/usr/bin/env python3
"""Zero-downtime collection swap via aliases.

The application always reads from `docs_live`. Build the new collection
alongside the old, then swap the alias atomically.

Companion to: https://computingforgeeks.com/qdrant-collections-guide/
"""
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

for n in ("docs_v1", "docs_v2"):
    if client.collection_exists(n):
        client.delete_collection(n)

# Original collection (e.g. MiniLM 384-dim)
client.create_collection(
    "docs_v1", models.VectorParams(size=384, distance=models.Distance.COSINE),
)
# New collection with upgraded model (e.g. BGE 768-dim)
client.create_collection(
    "docs_v2", models.VectorParams(size=768, distance=models.Distance.COSINE),
)

# Initial alias points at v1; the app reads from docs_live
client.update_collection_aliases(
    [
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(
                collection_name="docs_v1", alias_name="docs_live",
            )
        ),
    ]
)

# ...re-embed your corpus into docs_v2 here, at your own pace...

# Atomic swap: delete + create in a single transaction
client.update_collection_aliases(
    [
        models.DeleteAliasOperation(
            delete_alias=models.DeleteAlias(alias_name="docs_live")
        ),
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(
                collection_name="docs_v2", alias_name="docs_live",
            )
        ),
    ]
)

# Verify
all_aliases = client.get_aliases()
for a in all_aliases.aliases:
    print(f"alias={a.alias_name}  -> collection={a.collection_name}")
