"""Hybrid search on the same 100k-product collection.

Three queries side-by-side per term:
- dense only
- BM25 sparse only
- hybrid: dense + sparse via prefetch + Reciprocal Rank Fusion (RRF)

The collection must already exist with a dense (named "dense") and
sparse (named "bm25") vector — see load_ecommerce.py.
"""
from __future__ import annotations

import statistics
import time

from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding, TextEmbedding


URL = "http://localhost:6333"
COLLECTION = "products"

QUERIES = [
    "lightweight wireless headphones for travel",
    "professional camera with long battery life",
    "all-weather hiking boots",
    "noise-cancelling earbuds",
    "rugged outdoor backpack",
]


def show(label: str, results) -> None:
    print(f"  {label:<14}", end=" ")
    if not results:
        print("(no results)")
        return
    top = results[0]
    pid = top.id
    score = top.score
    desc = top.payload.get("description", "") if top.payload else ""
    print(f"top={pid:>6} score={score:7.4f} | {desc[:90]}")


def main() -> None:
    client = QdrantClient(url=URL, timeout=120)

    dense_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    sparse_model = SparseTextEmbedding("Qdrant/bm25")

    timings = {"dense": [], "sparse": [], "hybrid": []}

    for q in QUERIES:
        print()
        print(f"Query: {q!r}")
        dv = next(dense_model.embed([q])).tolist()
        sv = next(sparse_model.embed([q]))
        sparse_q = models.SparseVector(
            indices=sv.indices.tolist(),
            values=sv.values.tolist(),
        )

        # 1. Dense only
        t0 = time.perf_counter()
        r1 = client.query_points(
            collection_name=COLLECTION,
            query=dv, using="dense", limit=5, with_payload=True,
        ).points
        timings["dense"].append((time.perf_counter() - t0) * 1000)
        show("dense", r1)

        # 2. Sparse (BM25) only
        t0 = time.perf_counter()
        r2 = client.query_points(
            collection_name=COLLECTION,
            query=sparse_q, using="bm25", limit=5, with_payload=True,
        ).points
        timings["sparse"].append((time.perf_counter() - t0) * 1000)
        show("sparse BM25", r2)

        # 3. Hybrid: prefetch top-50 from each, then fuse with RRF, take top 5
        t0 = time.perf_counter()
        r3 = client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                models.Prefetch(query=dv, using="dense", limit=50),
                models.Prefetch(query=sparse_q, using="bm25", limit=50),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=5,
            with_payload=True,
        ).points
        timings["hybrid"].append((time.perf_counter() - t0) * 1000)
        show("hybrid RRF", r3)

    print()
    print("Timings (5 queries each)")
    print("=" * 60)
    for k in ("dense", "sparse", "hybrid"):
        v = sorted(timings[k])
        p50 = statistics.median(v)
        print(f"  {k:<8} min={v[0]:6.2f}  p50={p50:6.2f}  max={v[-1]:6.2f}  ms")


if __name__ == "__main__":
    main()
