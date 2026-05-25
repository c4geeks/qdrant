"""Retry pattern for transient Qdrant errors.

Wraps every call in exponential backoff with jitter. Demonstrates the
intentional 503 / NotReady handling that production clients need.
"""
import random
import time
from typing import Callable, TypeVar

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 5.0,
    retry_on: tuple[type[BaseException], ...] = (
        ResponseHandlingException,
        UnexpectedResponse,
        ConnectionError,
    ),
) -> T:
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            # Only retry on transient-looking failures.
            if isinstance(exc, UnexpectedResponse) and exc.status_code < 500:
                # 4xx are user errors, do not retry.
                raise
            if attempt == attempts - 1:
                raise
            sleep = min(max_delay, base_delay * (2 ** attempt))
            sleep += random.uniform(0, sleep * 0.25)
            print(f"  retry {attempt + 1}/{attempts} after {sleep*1000:.0f} ms: {exc}")
            time.sleep(sleep)
    raise RuntimeError("unreachable")


def main() -> None:
    client = QdrantClient(url="http://localhost:6333", api_key="PUT_YOUR_KEY_HERE")

    # Happy path
    info = with_retry(lambda: client.get_collection("docs"))
    print(f"docs collection status={info.status}  points={info.points_count}")

    # Simulate a 4xx that must NOT retry: query into a non-existent collection
    try:
        with_retry(lambda: client.get_collection("does-not-exist"))
    except UnexpectedResponse as exc:
        print(f"got expected 4xx (no retry): {exc.status_code}")

    # Burst: 50 concurrent-ish reads (sync, for clarity) with retry wrapper
    random.seed(3)
    successes = 0
    t0 = time.perf_counter()
    for _ in range(50):
        with_retry(lambda: client.count("docs", exact=True))
        successes += 1
    elapsed = time.perf_counter() - t0
    print(f"{successes}/50 reads ok in {elapsed*1000:.0f} ms")

    client.close()


if __name__ == "__main__":
    main()
