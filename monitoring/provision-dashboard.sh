#!/bin/bash
set -u
export KUBECONFIG=~/.kube_config

# Start port-forward to Grafana
kubectl port-forward -n monitoring svc/kps-grafana 8080:80 >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null' EXIT
sleep 5

# Discover prometheus datasource UID
DS_UID=$(curl -sS -u "admin:${GRAFANA_ADMIN_PASS}" http://localhost:8080/api/datasources \
         | jq -r '.[] | select(.type=="prometheus") | .uid' | head -1)
echo "Prometheus DS UID: $DS_UID"

# Patch the dashboard JSON with the real UID
sed "s/\"uid\": \"prometheus\"/\"uid\": \"${DS_UID}\"/g" /tmp/qdrant-dashboard.json > /tmp/dash-final.json

# Wrap with import shape
jq -n --slurpfile d /tmp/dash-final.json '{dashboard: $d[0], overwrite: true, folderId: 0}' > /tmp/dash-import.json

# Push
curl -sS -u "admin:${GRAFANA_ADMIN_PASS}" -X POST -H 'Content-Type: application/json' \
    http://localhost:8080/api/dashboards/db -d @/tmp/dash-import.json | jq .

# Sleep so the user can fetch the URL
sleep 2
