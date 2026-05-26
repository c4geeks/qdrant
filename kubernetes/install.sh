#!/usr/bin/env bash
# Stand up a 3-node Qdrant cluster on an existing Kubernetes cluster.
# Works on k3s (default storage = local-path), EKS (swap to gp3), GKE (pd-standard).
set -euo pipefail

NS="${NS:-qdrant}"
VALUES_FILE="${VALUES_FILE:-$(dirname "$0")/values.yaml}"

helm repo add qdrant https://qdrant.github.io/qdrant-helm 2>/dev/null || true
helm repo update qdrant

kubectl get namespace "${NS}" >/dev/null 2>&1 || kubectl create namespace "${NS}"

helm upgrade --install qdrant qdrant/qdrant -n "${NS}" -f "${VALUES_FILE}"

echo "Waiting for all pods to be Ready..."
kubectl rollout status statefulset/qdrant -n "${NS}" --timeout=300s

kubectl get pods,pvc,svc -n "${NS}" -o wide

echo
echo "Cluster ready. Quick smoke test:"
kubectl port-forward -n "${NS}" svc/qdrant 6333:6333 >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null' EXIT
sleep 3
curl -sS http://localhost:6333/cluster -H "api-key: $(grep ^apiKey "${VALUES_FILE}" | awk '{print $2}')" \
  | jq '{status: .result.status,
         peer_count: (.result.peers | length),
         leader: .result.raft_info.leader,
         term: .result.raft_info.term}'
