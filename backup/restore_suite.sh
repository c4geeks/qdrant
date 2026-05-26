#!/bin/bash
# Test three restore paths.
set -e
API="http://localhost:6333"

echo "=== Pre-restore state ==="
for C in articles products; do
  echo -n "$C: "
  curl -sS -X POST "${API}/collections/${C}/points/count" \
    -H "Content-Type: application/json" -d '{"exact": true}' | jq -c '.result'
done

echo
echo "=== A. Restore in place using PUT /collections/{name}/snapshots/recover ==="
SNAP=$(curl -sS "${API}/collections/articles/snapshots" | jq -r '.result[0].name')
echo "snapshot=$SNAP"
# Use a local file:// URL pointing at the actual snapshot file
SNAP_PATH="file:///qdrant/snapshots/articles/${SNAP}"
echo "snap_path=$SNAP_PATH"
RESP=$(curl -sS -X PUT "${API}/collections/articles/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d "{\"location\": \"${SNAP_PATH}\", \"priority\": \"snapshot\"}")
echo "$RESP" | jq .

echo
echo "=== Verify in-place restore preserved point count ==="
curl -sS -X POST "${API}/collections/articles/points/count" \
  -H "Content-Type: application/json" -d '{"exact": true}' | jq -c '.result'

echo
echo "=== B. Restore into a NEW collection name via /collections/{new}/snapshots/recover ==="
# Drop any existing 'articles_restore'
curl -sS -X DELETE "${API}/collections/articles_restore" > /dev/null
RESP=$(curl -sS -X PUT "${API}/collections/articles_restore/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d "{\"location\": \"${SNAP_PATH}\"}")
echo "$RESP" | jq .
sleep 1
echo "articles_restore: "
curl -sS -X POST "${API}/collections/articles_restore/points/count" \
  -H "Content-Type: application/json" -d '{"exact": true}' | jq -c '.result'

echo
echo "=== C. Restore from a downloaded snapshot URL (HTTP, not file://) ==="
# Drop any existing 'articles_http'
curl -sS -X DELETE "${API}/collections/articles_http" > /dev/null
# Qdrant fetches the URL itself
RESP=$(curl -sS -X PUT "${API}/collections/articles_http/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d "{\"location\": \"http://localhost:6333/collections/articles/snapshots/${SNAP}\"}")
echo "$RESP" | jq .
sleep 1
echo "articles_http: "
curl -sS -X POST "${API}/collections/articles_http/points/count" \
  -H "Content-Type: application/json" -d '{"exact": true}' | jq -c '.result'

echo
echo "=== Final state ==="
for C in articles articles_restore articles_http products; do
  COUNT=$(curl -sS -X POST "${API}/collections/${C}/points/count" \
    -H "Content-Type: application/json" -d '{"exact": true}' 2>/dev/null | jq -c '.result.count' || echo "missing")
  printf "  %-22s count=%s\n" "$C" "$COUNT"
done

echo
echo "=== D. Verify queried vectors match between original and restored ==="
# Get same point id from both, compare
PID=42
ORIG=$(curl -sS -X POST "${API}/collections/articles/points" \
  -H "Content-Type: application/json" \
  -d '{"ids": ['$PID'], "with_vector": true, "with_payload": true}' | jq -c '.result[0].payload')
REST=$(curl -sS -X POST "${API}/collections/articles_restore/points" \
  -H "Content-Type: application/json" \
  -d '{"ids": ['$PID'], "with_vector": true, "with_payload": true}' | jq -c '.result[0].payload')
echo "original payload: $ORIG"
echo "restored payload: $REST"
[ "$ORIG" = "$REST" ] && echo "PAYLOAD MATCH" || echo "PAYLOAD MISMATCH"
