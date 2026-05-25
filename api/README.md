# Qdrant REST and gRPC APIs in Practice

Companion to: https://computingforgeeks.com/qdrant-rest-grpc-api-guide/

Working clients for every operation Qdrant exposes, exercised against a
real cluster running v1.18.1 with API key auth enabled.

## Files

| File | Purpose |
|---|---|
| `rest_examples.sh` | curl walkthrough of collections, points, search, snapshots, cluster |
| `python_async.py` | REST async vs gRPC sync benchmark on 5,000 points |
| `grpc_client.py` | Native Python gRPC stubs (no high-level wrapper) |
| `retry_demo.py` | Retry-with-backoff pattern, 4xx-aware |
| `go/main.go` | Official Go SDK end-to-end |
| `go/go.mod` | Go module manifest |

## Setup

```bash
# Bring up Qdrant with API key auth
mkdir -p /opt/qdrant/storage /opt/qdrant/snapshots
sudo chown -R 1000:1000 /opt/qdrant
sudo docker run -d --name qdrant --restart=always \
  -p 6333:6333 -p 6334:6334 \
  -e QDRANT__SERVICE__API_KEY=PUT_YOUR_KEY_HERE \
  -v /opt/qdrant/storage:/qdrant/storage \
  -v /opt/qdrant/snapshots:/qdrant/snapshots \
  qdrant/qdrant:v1.18.1

# Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Go
cd go && go mod tidy
```

## Run

```bash
bash rest_examples.sh             # curl walkthrough
python3 python_async.py           # REST async vs gRPC sync benchmark
python3 grpc_client.py            # native gRPC stubs
python3 retry_demo.py             # retry pattern
cd go && go run main.go           # Go SDK
```

Tested 2026-05 on Ubuntu 24.04 with Qdrant 1.18.1, qdrant-client 1.18.0,
Go 1.22.2, grpcio 1.80.

## Gotchas these scripts catch

- REST upserts hit a 32 MiB JSON payload cap around 5,000 points of 384-dim
  vectors. Batch in groups of 1,000.
- gRPC client defaults to TLS when an api_key is set. Pass `https=False`
  in Python and `UseTLS: false` in Go when the server has TLS off.
- Native gRPC stubs need `VectorInput(dense=DenseVector(data=...))`, not
  bare `Vector`. Mixing them produces a protobuf type error.
- `query_points` wraps results inside `.result.points[]`. Older `/search`
  filters that hit `.result[]` directly will fail jq.
- The Web UI Console adds a `/dashboard/` baseURL on requests. A curl
  command that works from a shell will 404 in the Console unless you skip
  the leading slash on the verb line.
