"""Benchmark filter latency before and after building payload indexes.

The dataset is the 100k-product collection from load_ecommerce.py. We
run six representative queries: 3 pure filter (no vector), 3 vector +
filter. Each batch runs 50 times, sorted, and we print p50/p95/max.
"""
from __future__ import annotations

import random
import statistics
import time

from qdrant_client import QdrantClient, models

URL = "http://localhost:6333"
COLLECTION = "products"
DENSE_DIM = 384


def stats(label: str, samples_ms: list[float]) -> None:
    samples_ms.sort()
    p50 = statistics.median(samples_ms)
    p95 = samples_ms[int(len(samples_ms) * 0.95) - 1]
    print(
        f"  {label:<32} n={len(samples_ms):>3}  "
        f"min={samples_ms[0]:7.2f}  p50={p50:7.2f}  "
        f"p95={p95:7.2f}  max={samples_ms[-1]:8.2f}  ms"
    )


def run_query_set(client: QdrantClient, runs: int, query_vec: list[float]) -> None:
    # 1. Pure filter — exact-match keyword + range
    f1 = models.Filter(must=[
        models.FieldCondition(key="category", match=models.MatchValue(value="Laptops")),
        models.FieldCondition(key="price", range=models.Range(gte=200, lte=800)),
    ])
    # 2. Pure filter — bool + datetime range
    f2 = models.Filter(must=[
        models.FieldCondition(key="in_stock", match=models.MatchValue(value=True)),
        models.FieldCondition(
            key="created_at",
            range=models.DatetimeRange(gte="2026-01-01T00:00:00Z"),
        ),
    ])
    # 3. Pure filter — geo_radius (1000 km around London)
    f3 = models.Filter(must=[
        models.FieldCondition(
            key="location",
            geo_radius=models.GeoRadius(
                center=models.GeoPoint(lon=-0.1276, lat=51.5072),
                radius=1_000_000,
            ),
        ),
    ])
    # 4. Vector + must keyword + range
    f4 = models.Filter(must=[
        models.FieldCondition(key="brand", match=models.MatchValue(value="Acme")),
        models.FieldCondition(key="rating", range=models.Range(gte=4.0)),
    ])
    # 5. Vector + must_not
    f5 = models.Filter(must_not=[
        models.FieldCondition(key="category", match=models.MatchValue(value="Books")),
    ])
    # 6. Vector + complex must/should
    f6 = models.Filter(
        must=[models.FieldCondition(key="price", range=models.Range(lte=500))],
        should=[
            models.FieldCondition(key="brand", match=models.MatchValue(value="Stark")),
            models.FieldCondition(key="brand", match=models.MatchValue(value="Wayne")),
        ],
    )

    print()
    print("  -- Pure filter (no vector) --")
    for label, flt in [("category+price", f1), ("bool+datetime", f2), ("geo_radius 1000km", f3)]:
        t = []
        for _ in range(runs):
            t0 = time.perf_counter()
            client.scroll(collection_name=COLLECTION, scroll_filter=flt, limit=20, with_payload=False)
            t.append((time.perf_counter() - t0) * 1000)
        stats(label, t)

    print("  -- Vector search + filter --")
    for label, flt in [("brand+rating", f4), ("must_not Books", f5), ("must+should", f6)]:
        t = []
        for _ in range(runs):
            t0 = time.perf_counter()
            client.query_points(
                collection_name=COLLECTION,
                query=query_vec,
                using="dense",
                query_filter=flt,
                limit=10,
                with_payload=False,
            )
            t.append((time.perf_counter() - t0) * 1000)
        stats(label, t)


def main() -> None:
    client = QdrantClient(url=URL, timeout=120)

    info = client.get_collection(COLLECTION)
    print(f"Collection ready: {info.points_count} points, status={info.status}")

    random.seed(1)
    query_vec = [random.uniform(-1, 1) for _ in range(DENSE_DIM)]

    print()
    print("BEFORE building payload indexes")
    print("=" * 70)
    run_query_set(client, runs=50, query_vec=query_vec)

    print()
    print("Building payload indexes...")
    t0 = time.perf_counter()

    # keyword (is_tenant for category — splits the index per tenant)
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="category",
        field_schema=models.KeywordIndexParams(type="keyword", is_tenant=True),
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="brand",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="price",
        field_schema=models.PayloadSchemaType.FLOAT,
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="rating",
        field_schema=models.PayloadSchemaType.FLOAT,
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="in_stock",
        field_schema=models.PayloadSchemaType.BOOL,
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="created_at",
        field_schema=models.PayloadSchemaType.DATETIME,
        wait=True,
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="location",
        field_schema=models.PayloadSchemaType.GEO,
        wait=True,
    )
    # full-text on description
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="description",
        field_schema=models.TextIndexParams(
            type="text",
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=20,
            lowercase=True,
        ),
        wait=True,
    )
    print(f"  built 8 payload indexes in {time.perf_counter() - t0:.1f}s")

    # Let any merges settle
    time.sleep(5)
    info = client.get_collection(COLLECTION)
    print(f"  payload schema: {sorted(info.payload_schema.keys())}")

    print()
    print("AFTER building payload indexes")
    print("=" * 70)
    run_query_set(client, runs=50, query_vec=query_vec)

    # One extra: full-text match (only works after the text index)
    print()
    print("  -- After: full-text payload match --")
    txt = models.Filter(must=[
        models.FieldCondition(key="description", match=models.MatchText(text="wireless travel")),
    ])
    t = []
    for _ in range(50):
        t0 = time.perf_counter()
        client.scroll(collection_name=COLLECTION, scroll_filter=txt, limit=20, with_payload=False)
        t.append((time.perf_counter() - t0) * 1000)
    stats("match_text 'wireless travel'", t)


if __name__ == "__main__":
    main()
