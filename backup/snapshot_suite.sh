#!/bin/bash
# Full snapshot CRUD exercised on a real cluster.
set -e
API="http://localhost:6333"

echo "=== 1. Per-collection snapshot: articles ==="
t0=$(date +%s.%N)
RESP=$(curl -sS -X POST "${API}/collections/articles/snapshots")
echo "$RESP" | jq .
t1=$(date +%s.%N)
echo "create time: $(echo "$t1-$t0" | bc) s"
ARTICLES_SNAP=$(echo "$RESP" | jq -r '.result.name')
echo "ARTICLES_SNAP=$ARTICLES_SNAP"

echo
echo "=== 2. Per-collection snapshot: products ==="
RESP=$(curl -sS -X POST "${API}/collections/products/snapshots")
echo "$RESP" | jq .
PRODUCTS_SNAP=$(echo "$RESP" | jq -r '.result.name')

echo
echo "=== 3. List snapshots per collection ==="
curl -sS "${API}/collections/articles/snapshots" | jq .
curl -sS "${API}/collections/products/snapshots" | jq .

echo
echo "=== 4. Snapshot files on disk + sizes ==="
sudo ls -la /opt/qdrant/snapshots/
sudo du -sh /opt/qdrant/snapshots/*/

echo
echo "=== 5. Cluster-wide snapshot ==="
t0=$(date +%s.%N)
RESP=$(curl -sS -X POST "${API}/snapshots")
echo "$RESP" | jq .
t1=$(date +%s.%N)
echo "create time: $(echo "$t1-$t0" | bc) s"
FULL_SNAP=$(echo "$RESP" | jq -r '.result.name')

echo
echo "=== 6. List full snapshots ==="
curl -sS "${API}/snapshots" | jq .
sudo ls -la /opt/qdrant/snapshots/

echo
echo "=== 7. Download the articles snapshot (streamed) ==="
curl -sS -o /tmp/articles.snapshot "${API}/collections/articles/snapshots/${ARTICLES_SNAP}"
ls -lh /tmp/articles.snapshot
file /tmp/articles.snapshot

# Save snapshot names for the restore + S3 stages
echo "$ARTICLES_SNAP" > /tmp/articles_snap.txt
echo "$PRODUCTS_SNAP" > /tmp/products_snap.txt
echo "$FULL_SNAP" > /tmp/full_snap.txt
