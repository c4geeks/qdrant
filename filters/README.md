# Qdrant Filters and Payload Indexes

Companion to: https://computingforgeeks.com/qdrant-filter-payload-index/

Working scripts that exercise the full Qdrant 1.18.1 filter surface on
a real 100,000-product e-commerce dataset.

## Files

| File | Purpose |
|---|---|
| `load_ecommerce.py` | Build the 100k-product collection (dense BGE-small + BM25 sparse, 8-field payload) |
| `benchmark_filter.py` | Measure p50/p95/max for 6 filter shapes, before and after payload indexes |
| `hybrid_search.py` | Compare dense / sparse / hybrid (RRF) on 5 product queries |

## Setup

```bash
# Bring Qdrant up
sudo docker run -d --name qdrant --restart=always \
  -p 6333:6333 -p 6334:6334 \
  -v /opt/qdrant/storage:/qdrant/storage \
  qdrant/qdrant:v1.18.1

# Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 load_ecommerce.py        # ~16 min on a 4-core VM (embedding-bound)
python3 benchmark_filter.py      # ~30 s, before+after benchmark
python3 hybrid_search.py         # ~5 s, dense vs sparse vs hybrid
```

## Measured results (Qdrant 1.18.1 / 100k products / 4 vCPU)

| Query | Before index (p50) | After index (p50) | Speedup |
|---|---:|---:|---:|
| Vector + brand + rating | 146.77 ms | 2.36 ms | **62x** |
| Vector + must+should | 13.02 ms | 1.70 ms | 7.7x |
| Vector + must_not | 4.84 ms | 1.86 ms | 2.6x |
| Pure category+price | 2.69 ms | 1.00 ms | 2.7x |
| Pure bool+datetime | 1.45 ms | 0.99 ms | 1.5x |
| Pure geo_radius | 1.18 ms | 0.98 ms | 1.2x |

All 8 payload indexes built in 4.7 s.

Hybrid timing: dense p50 = 2.49 ms, BM25 sparse p50 = 1.85 ms, hybrid RRF p50 = 4.68 ms.

## Gotchas these scripts catch

- **Geo payload is lon/lat**, not lat/lon. Opposite of most map libraries.
- **Datetime filters need RFC3339 with timezone** (trailing `Z` or `+02:00`).
  A naive `"2026-05-25"` is rejected.
- **Full-text needs `TextIndexParams` with a tokenizer.** The bare
  `PayloadSchemaType.TEXT` does not produce a `match_text`-usable index.
- **`indexing_threshold` is per-segment.** A 100k collection across 8
  segments may have zero HNSW-indexed vectors if each is under 20k.
- **`using=` is required** on named-vector collections. Omitting it on a
  `query_points` call raises 400 "vector name is required".

Tested 2026-05 on Ubuntu 24.04 with Qdrant 1.18.1, qdrant-client 1.18.0,
fastembed 0.8.0.
