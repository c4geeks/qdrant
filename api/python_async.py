"""REST async + gRPC sync benchmark against the same cluster.

Times 100 calls of each and prints min / p50 / p95 / max in ms.
"""
import asyncio
import random
import statistics
import time

from qdrant_client import AsyncQdrantClient, QdrantClient, models

URL_REST = "http://localhost:6333"
URL_GRPC_HOST = "localhost"
URL_GRPC_PORT = 6334
API_KEY = "PUT_YOUR_KEY_HERE"

random.seed(7)
QUERY = [round(random.random(), 4) for _ in range(384)]


def stats(label: str, samples_ms: list[float]) -> None:
    samples_ms.sort()
    p50 = statistics.median(samples_ms)
    p95 = samples_ms[int(len(samples_ms) * 0.95) - 1]
    print(
        f"{label:24}  n={len(samples_ms)}  "
        f"min={samples_ms[0]:6.2f}  p50={p50:6.2f}  "
        f"p95={p95:6.2f}  max={samples_ms[-1]:6.2f}  ms"
    )


async def bench_rest_async() -> list[float]:
    client = AsyncQdrantClient(url=URL_REST, api_key=API_KEY)
    times: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        await client.query_points(collection_name="docs", query=QUERY, limit=5)
        times.append((time.perf_counter() - t0) * 1000)
    await client.close()
    return times


def bench_grpc_sync() -> list[float]:
    client = QdrantClient(
        host=URL_GRPC_HOST,
        grpc_port=URL_GRPC_PORT,
        prefer_grpc=True,
        https=False,
        api_key=API_KEY,
    )
    times: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        client.query_points(collection_name="docs", query=QUERY, limit=5)
        times.append((time.perf_counter() - t0) * 1000)
    client.close()
    return times


async def bench_rest_concurrent() -> tuple[float, float]:
    """Send 100 queries with asyncio.gather to measure throughput."""
    client = AsyncQdrantClient(url=URL_REST, api_key=API_KEY)
    t0 = time.perf_counter()
    await asyncio.gather(
        *(
            client.query_points(collection_name="docs", query=QUERY, limit=5)
            for _ in range(100)
        )
    )
    elapsed = time.perf_counter() - t0
    await client.close()
    return elapsed, 100 / elapsed


def main() -> None:
    # Make sure the collection has enough points for a realistic search load.
    bootstrap = QdrantClient(url=URL_REST, api_key=API_KEY)
    if bootstrap.collection_exists("docs"):
        bootstrap.delete_collection("docs")
    bootstrap.create_collection(
        "docs", vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
    )
    random.seed(0)
    total = 5000
    batch_size = 1000
    for start in range(0, total, batch_size):
        batch = [
            models.PointStruct(
                id=i,
                vector=[random.random() for _ in range(384)],
                payload={"category": random.choice(["docs", "blog", "ref"]), "price": i % 100},
            )
            for i in range(start, min(start + batch_size, total))
        ]
        bootstrap.upsert("docs", points=batch, wait=True)
    print(f"Seeded 'docs' with {bootstrap.count('docs', exact=True).count} points")
    bootstrap.close()

    rest_times = asyncio.run(bench_rest_async())
    grpc_times = bench_grpc_sync()

    print()
    stats("REST async (HTTP/1.1)", rest_times)
    stats("gRPC sync (HTTP/2)", grpc_times)

    elapsed, rps = asyncio.run(bench_rest_concurrent())
    print()
    print(f"REST async 100-in-parallel  total={elapsed*1000:.1f} ms  ~{rps:.0f} req/s")


if __name__ == "__main__":
    main()
