#!/bin/bash
# End-to-end S3 backup + restore round-trip.
set -e

API="http://localhost:6333"
BUCKET="${BUCKET:-cfg-lab-qdrant-snapshots-1779810367}"
REGION="${REGION:-eu-west-1}"

echo "=== 1. Trigger fresh snapshots for both collections ==="
for C in articles products; do
  RESP=$(curl -sS -X POST "${API}/collections/${C}/snapshots")
  NAME=$(echo "$RESP" | jq -r '.result.name')
  printf "  %-10s %s  (%s bytes)\n" "$C" "$NAME" "$(echo "$RESP" | jq '.result.size')"
done

echo
echo "=== 2. Upload snapshots dir to S3 with aws s3 sync ==="
TS=$(date -u +%Y%m%dT%H%M%SZ)
PREFIX="s3://${BUCKET}/${TS}/"
echo "prefix=${PREFIX}"
t0=$(date +%s.%N)
sudo aws s3 sync /opt/qdrant/snapshots/ "${PREFIX}" \
  --exclude "tmp/*" --exclude "*.tmp" \
  --no-progress 2>&1 | tail -10
t1=$(date +%s.%N)
echo "sync time: $(echo "$t1-$t0" | bc) s"

echo
echo "=== 3. S3 listing after upload ==="
aws s3 ls --recursive "s3://${BUCKET}/" --human-readable | head -10

echo
echo "=== 4. Simulate disaster: delete the articles collection ==="
curl -sS -X DELETE "${API}/collections/articles" | jq -c .
echo "Now collections:"
curl -sS "${API}/collections" | jq -c '.result.collections'

echo
echo "=== 5. Download snapshot from S3, restore ==="
SNAP=$(aws s3 ls "${PREFIX}articles/" | awk '$NF ~ /\.snapshot$/ {print $NF}' | tail -1)
echo "Restoring: ${SNAP}"
aws s3 cp "${PREFIX}articles/${SNAP}" /tmp/restore.snapshot --quiet
ls -lh /tmp/restore.snapshot
# Push the file into Qdrant snapshots dir then recover
sudo mkdir -p /opt/qdrant/snapshots/articles
sudo cp /tmp/restore.snapshot "/opt/qdrant/snapshots/articles/${SNAP}"
RESP=$(curl -sS -X PUT "${API}/collections/articles/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d "{\"location\": \"file:///qdrant/snapshots/articles/${SNAP}\", \"priority\": \"snapshot\"}")
echo "$RESP" | jq .

echo
echo "=== 6. Verify the disaster-recovery succeeded ==="
COUNT=$(curl -sS -X POST "${API}/collections/articles/points/count" \
  -H "Content-Type: application/json" -d '{"exact": true}' | jq -c '.result.count')
echo "articles count after S3 restore: ${COUNT}"

# Spot-check a known payload
PAYLOAD=$(curl -sS -X POST "${API}/collections/articles/points" \
  -H "Content-Type: application/json" \
  -d '{"ids": [42], "with_payload": true}' | jq -c '.result[0].payload')
echo "point 42 payload: ${PAYLOAD}"

echo
echo "=== 7. Cleanup the test artifacts ==="
rm -f /tmp/restore.snapshot
