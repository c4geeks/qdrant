#!/usr/bin/env bash
# Snapshot every Qdrant collection and sync to S3.
# Drop into /usr/local/bin/qdrant-backup.sh and wire a systemd timer.
set -euo pipefail

API="${QDRANT_API:-http://localhost:6333}"
API_KEY="${QDRANT_API_KEY:-}"
BUCKET="${BUCKET:?BUCKET env var is required, e.g. cfg-qdrant-snapshots}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-/opt/qdrant/snapshots}"

auth=()
[[ -n "$API_KEY" ]] && auth=(-H "api-key: $API_KEY")

# Snapshot every collection
for C in $(curl -sS "${auth[@]}" "${API}/collections" | jq -r '.result.collections[].name'); do
    curl -sS -X POST "${auth[@]}" "${API}/collections/${C}/snapshots" > /dev/null
    echo "snapshot taken: ${C}"
done

# Sync to S3 with date prefix
TS="$(date -u +%Y%m%dT%H%M%SZ)"
aws s3 sync "${SNAPSHOT_DIR}/" "s3://${BUCKET}/${TS}/" \
    --exclude "tmp/*" --exclude "*.tmp" --no-progress

# Local rotation: keep the 24 most recent snapshots per collection
for D in "${SNAPSHOT_DIR}"/*/; do
    ls -t "${D}"*.snapshot 2>/dev/null | tail -n +25 | xargs -r rm -v
done

echo "qdrant-backup ${TS} complete"
