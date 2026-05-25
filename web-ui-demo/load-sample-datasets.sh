#!/usr/bin/env bash
# Load the three official Qdrant sample-dataset snapshots into a running cluster.
# Same payload as clicking "Import" in the dashboard's Datasets panel.
# Companion to: https://computingforgeeks.com/qdrant-web-ui-guide/
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
API_KEY="${QDRANT_API_KEY:-}"

snaps=(
  "midlib|midlib-v1.16.0.snapshot"
  "qdrant-web-site-docs|qdrant-web-site-docs-2024-04-05-v1.16.0.snapshot"
  "prefix-cache|prefix-cache-v1.16.0.snapshot"
)

curl_auth=()
if [ -n "$API_KEY" ]; then
  curl_auth=(-H "api-key: $API_KEY")
fi

echo "==> Cluster: $QDRANT_URL"
curl -fsS "${curl_auth[@]}" "$QDRANT_URL/" | python3 -m json.tool

for pair in "${snaps[@]}"; do
  name="${pair%%|*}"
  file="${pair##*|}"
  echo "==> Importing $file -> collection '$name'"
  curl -fsS "${curl_auth[@]}" -X PUT \
    "$QDRANT_URL/collections/$name/snapshots/recover" \
    -H "Content-Type: application/json" \
    --data "{\"location\":\"https://snapshots.qdrant.io/$file\"}" \
    | python3 -m json.tool
done

echo "==> Collections after import:"
curl -fsS "${curl_auth[@]}" "$QDRANT_URL/collections" | python3 -m json.tool
