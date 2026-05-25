"""Native gRPC client against Qdrant.

Uses the stubs generated inside qdrant-client itself (qdrant_client.grpc),
so no protoc step is needed for Python. For Go, you generate from .proto.
"""
import random
import time

import grpc
from qdrant_client.grpc import (
    CollectionsStub,
    CreateCollection,
    Distance,
    PointId,
    PointsStub,
    PointStruct,
    QueryPoints,
    UpsertPoints,
    Value,
    Vector,
    VectorParams,
    VectorsConfig,
)
from qdrant_client.grpc import Vectors

API_KEY = "PUT_YOUR_KEY_HERE"


def add_auth(metadata: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return metadata + [("api-key", API_KEY)]


def main() -> None:
    channel = grpc.insecure_channel("localhost:6334")
    collections = CollectionsStub(channel)
    points = PointsStub(channel)

    print("=== gRPC: list collections ===")
    from qdrant_client.grpc import ListCollectionsRequest
    resp = collections.List(
        ListCollectionsRequest(),
        metadata=add_auth([]),
    )
    for c in resp.collections:
        print(f"  - {c.name}")

    print()
    print("=== gRPC: create collection 'grpc_demo' ===")
    from qdrant_client.grpc import DeleteCollection
    try:
        collections.Delete(
            DeleteCollection(collection_name="grpc_demo"),
            metadata=add_auth([]),
        )
    except grpc.RpcError:
        pass
    create_resp = collections.Create(
        CreateCollection(
            collection_name="grpc_demo",
            vectors_config=VectorsConfig(
                params=VectorParams(size=8, distance=Distance.Cosine),
            ),
        ),
        metadata=add_auth([]),
    )
    print(f"  created={create_resp.result}  ({create_resp.time:.3f}s)")

    print()
    print("=== gRPC: upsert 5 points ===")
    random.seed(11)
    pts = [
        PointStruct(
            id=PointId(num=i),
            vectors=Vectors(vector=Vector(data=[random.random() for _ in range(8)])),
            payload={"category": Value(string_value=f"c{i % 3}")},
        )
        for i in range(5)
    ]
    upsert_resp = points.Upsert(
        UpsertPoints(collection_name="grpc_demo", points=pts, wait=True),
        metadata=add_auth([]),
    )
    print(f"  status={upsert_resp.result.status}  op_id={upsert_resp.result.operation_id}  ({upsert_resp.time:.3f}s)")

    print()
    print("=== gRPC: query_points ===")
    from qdrant_client.grpc import VectorInput, Query, DenseVector
    random.seed(12)
    q_vec = [random.random() for _ in range(8)]
    t0 = time.perf_counter()
    qr = points.Query(
        QueryPoints(
            collection_name="grpc_demo",
            query=Query(nearest=VectorInput(dense=DenseVector(data=q_vec))),
            limit=3,
        ),
        metadata=add_auth([]),
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    for r in qr.result:
        pid = r.id.num if r.id.HasField("num") else r.id.uuid
        print(f"  id={pid}  score={r.score:.4f}")
    print(f"  wall={elapsed_ms:.2f} ms  server_time={qr.time*1000:.2f} ms")

    channel.close()


if __name__ == "__main__":
    main()
