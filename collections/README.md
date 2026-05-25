# Qdrant Collections: Create, Configure, and Manage Vectors

Companion to: https://computingforgeeks.com/qdrant-collections-guide/

Working Python scripts for every collection-level pattern Qdrant supports.
Each file is independent and idempotent (re-running drops and recreates).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Local cluster on port 6333 — see ../install-ubuntu/, ../install-rocky/,
# or ../install-debian/ for the install paths.
```

## Files

| Script | Pattern |
|---|---|
| `create_collection.py` | Basic single dense vector, Cosine distance |
| `create_with_named_vectors.py` | One collection, multiple vector spaces (text + image) |
| `create_with_sparse.py` | Dense + sparse vector in the same collection |
| `payload_indexes.py` | All 7 payload index types (keyword/int/float/bool/geo/text/datetime) |
| `on_disk_collection.py` | Memory-frugal: vectors + payload + HNSW graph on disk |
| `multitenant.py` | Multi-tenancy via `is_tenant=True` keyword index |
| `optimizer_and_wal.py` | Optimizer + WAL config tuning |
| `alias_swap.py` | Zero-downtime collection swap via atomic alias update |

Tested 2026-05 on Ubuntu 24.04 with Qdrant 1.18.1 and qdrant-client 1.18.0.

## Gotchas this catches

- **Distance and vector size are immutable**: pick correctly the first
  time, or plan an alias swap to migrate. `update_collection` cannot
  change either.
- **Geo payload is lon/lat, not lat/lon**: opposite of most map APIs.
- **Text index needs explicit tokenizer params**: a plain string field
  is not searchable with `match_text` until you create a
  `TextIndexParams` index on it. Tokenizer choice (`WORD`,
  `WHITESPACE`, `PREFIX`, `MULTILINGUAL`) is part of the index, not the
  query.
- **`indexing_threshold` is per-segment**: a collection of 100k points
  spread across 8 segments may not have any HNSW indexes yet if each
  segment is below the threshold. Check `indexed_vectors_count` on the
  Info tab.
- **Aliases are not collections**: `get_collection(alias_name)` fails.
  Aliases resolve on the wire but do not appear in
  `get_collections()`. Use `get_aliases()` to inspect.
