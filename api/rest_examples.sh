#!/bin/bash
# REST suite exercised on a real cluster.
# Captures actual responses so we have real evidence for the article.
set -e

API="http://localhost:6333"
KEY="PUT_YOUR_KEY_HERE"
H_AUTH=(-H "api-key: ${KEY}")
H_JSON=(-H "Content-Type: application/json")

echo "=== 1. Telemetry / version ==="
curl -sS "${H_AUTH[@]}" "${API}/" | jq .

echo
echo "=== 2. Create collection 'docs' (Cosine, 384-dim) ==="
curl -sS -X PUT "${API}/collections/docs" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{
  "vectors": {"size": 384, "distance": "Cosine"}
}' | jq .

echo
echo "=== 3. List collections ==="
curl -sS "${H_AUTH[@]}" "${API}/collections" | jq .

echo
echo "=== 4. Get collection detail ==="
curl -sS "${H_AUTH[@]}" "${API}/collections/docs" | jq '{status:.result.status, points_count:.result.points_count, config:.result.config.params}'

echo
echo "=== 5. Upsert 3 points (batch) ==="
curl -sS -X PUT "${API}/collections/docs/points?wait=true" "${H_AUTH[@]}" "${H_JSON[@]}" -d "{
  \"points\": [
    {\"id\": 1, \"vector\": $(python3 -c 'import random;random.seed(1);print([round(random.random(),4) for _ in range(384)])'), \"payload\": {\"title\": \"Intro to vectors\", \"category\": \"basics\", \"price\": 0}},
    {\"id\": 2, \"vector\": $(python3 -c 'import random;random.seed(2);print([round(random.random(),4) for _ in range(384)])'), \"payload\": {\"title\": \"HNSW deep dive\", \"category\": \"index\", \"price\": 29}},
    {\"id\": 3, \"vector\": $(python3 -c 'import random;random.seed(3);print([round(random.random(),4) for _ in range(384)])'), \"payload\": {\"title\": \"Filter cookbook\", \"category\": \"filters\", \"price\": 19}}
  ]
}" | jq .

echo
echo "=== 6. Count points ==="
curl -sS -X POST "${API}/collections/docs/points/count" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{"exact": true}' | jq .

echo
echo "=== 7. Retrieve points by id ==="
curl -sS -X POST "${API}/collections/docs/points" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{
  "ids": [1, 2, 3], "with_payload": true, "with_vector": false
}' | jq '.result[] | {id, payload}'

echo
echo "=== 8. Modern query_points (with filter) ==="
curl -sS -X POST "${API}/collections/docs/points/query" "${H_AUTH[@]}" "${H_JSON[@]}" -d "{
  \"query\": $(python3 -c 'import random;random.seed(1);print([round(random.random(),4) for _ in range(384)])'),
  \"limit\": 3,
  \"with_payload\": true,
  \"filter\": {
    \"must\": [{\"key\": \"category\", \"match\": {\"value\": \"index\"}}]
  }
}" | jq '.result.points[] | {id, score, payload}'

echo
echo "=== 9. Scroll (no vector search, just iterate) ==="
curl -sS -X POST "${API}/collections/docs/points/scroll" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{
  "limit": 10, "with_payload": true, "with_vector": false
}' | jq '.result.points[] | {id, payload}'

echo
echo "=== 10. Create snapshot ==="
SNAP_NAME=$(curl -sS -X POST "${API}/collections/docs/snapshots" "${H_AUTH[@]}" | jq -r '.result.name')
echo "snapshot=$SNAP_NAME"
curl -sS "${H_AUTH[@]}" "${API}/collections/docs/snapshots" | jq .

echo
echo "=== 11. Cluster status ==="
curl -sS "${H_AUTH[@]}" "${API}/cluster" | jq .

echo
echo "=== 12. Delete points by filter ==="
curl -sS -X POST "${API}/collections/docs/points/delete?wait=true" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{
  "filter": {"must": [{"key": "price", "range": {"lt": 20}}]}
}' | jq .
curl -sS -X POST "${API}/collections/docs/points/count" "${H_AUTH[@]}" "${H_JSON[@]}" -d '{"exact": true}' | jq .

echo
echo "=== 13. Latency probe (10 query_points calls) ==="
python3 - <<'PY'
import json, subprocess, time, statistics, random, os
random.seed(99)
v = [round(random.random(), 4) for _ in range(384)]
body = json.dumps({"query": v, "limit": 5})
times = []
for _ in range(10):
    t0 = time.perf_counter()
    subprocess.run(["curl","-sS","-X","POST",
                    "http://localhost:6333/collections/docs/points/query",
                    "-H","api-key: PUT_YOUR_KEY_HERE",
                    "-H","Content-Type: application/json",
                    "-d", body], capture_output=True, check=True)
    times.append((time.perf_counter()-t0)*1000)
times.sort()
print(f"REST query_points  n=10  min={times[0]:.2f} p50={statistics.median(times):.2f} max={times[-1]:.2f} ms")
PY
