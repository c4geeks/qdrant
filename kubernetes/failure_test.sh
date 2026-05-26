#!/bin/bash
# Continuous query loop during a pod kill — verify zero downtime.
set -u
KEY="CHANGE_ME_TO_A_STRONG_KEY"

# Start port-forward to the service so traffic round-robins
export KUBECONFIG=~/.kube_config
kubectl port-forward -n qdrant svc/qdrant 6333:6333 >/dev/null 2>&1 &
PF=$!
sleep 3
trap 'kill $PF 2>/dev/null' EXIT

# Query payload — 384 dummy floats (matches dim)
QUERY=$(python3 -c "import random; random.seed(7); print('['+','.join(str(round(random.random(),4)) for _ in range(384))+']')")
BODY="{\"query\": ${QUERY}, \"limit\": 5}"

echo "== Baseline: 20 queries, all should succeed =="
ok=0; fail=0
for i in $(seq 1 20); do
    code=$(curl -sS -o /dev/null -w '%{http_code}' \
        http://localhost:6333/collections/articles/points/query \
        -H "api-key: $KEY" -H "Content-Type: application/json" -d "$BODY")
    [ "$code" = "200" ] && ok=$((ok+1)) || fail=$((fail+1))
done
echo "  baseline: ok=$ok fail=$fail"

echo
echo "== Disaster: kill qdrant-2 pod =="
echo "$(date '+%H:%M:%S.%3N') START"
kubectl delete pod qdrant-2 -n qdrant --grace-period=0 --force &
echo "$(date '+%H:%M:%S.%3N') pod deletion command sent"

ok=0; fail=0
errors=""
declare -A status_count
for i in $(seq 1 60); do
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 \
        http://localhost:6333/collections/articles/points/query \
        -H "api-key: $KEY" -H "Content-Type: application/json" -d "$BODY")
    status_count[$code]=$(( ${status_count[$code]:-0} + 1 ))
    [ "$code" = "200" ] && ok=$((ok+1)) || fail=$((fail+1))
    sleep 0.2
done
echo "$(date '+%H:%M:%S.%3N') END  60 queries during the outage"
echo "  during failure: ok=$ok fail=$fail"
echo "  status codes:"
for c in "${!status_count[@]}"; do
    echo "    $c: ${status_count[$c]}"
done

echo
echo "== State after the failure =="
kubectl get pods -n qdrant
sleep 8
echo
kubectl get pods -n qdrant
