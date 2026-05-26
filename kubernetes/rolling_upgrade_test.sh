#!/bin/bash
# Run a continuous GET /collections/articles loop FROM INSIDE the cluster
# while doing a rolling upgrade. Simpler request, accurate uptime probe.
set -u
KEY="CHANGE_ME_TO_A_STRONG_KEY"
export KUBECONFIG=~/.kube_config

# Roll back first
kubectl rollout status statefulset/qdrant -n qdrant --timeout=300s >/dev/null 2>&1

echo "=== Starting in-cluster query loop ==="
# Use a simple readiness probe — GET /collections/articles
# Returns 200 if the service can reach a healthy pod
kubectl delete pod query-loop -n qdrant --ignore-not-found --grace-period=0 --force 2>&1 | tail -1
kubectl run -n qdrant query-loop --image=curlimages/curl --restart=Never -- \
  sh -c "
    end=\$((\$(date +%s) + 600))
    while [ \$(date +%s) -lt \$end ]; do
      code=\$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 \
        http://qdrant:6333/collections/articles \
        -H 'api-key: $KEY')
      echo \"\$(date '+%H:%M:%S') \$code\"
      sleep 0.5
    done
  " 2>/dev/null

# Wait for pod Running
for i in $(seq 1 20); do
  phase=$(kubectl get pod query-loop -n qdrant -o jsonpath='{.status.phase}' 2>/dev/null)
  [ "$phase" = "Running" ] && break
  sleep 1
done
echo "loop pod: $phase"

# Stream logs in background
kubectl logs -n qdrant -f query-loop > /tmp/in-cluster.log 2>&1 &
LOG_PID=$!
sleep 4
echo "Baseline (first 5 entries):"
head -5 /tmp/in-cluster.log

echo
echo "$(date '+%H:%M:%S') TRIGGER rolling upgrade v1.18.1 -> v1.18.0"
helm upgrade qdrant qdrant/qdrant -n qdrant --reuse-values --set image.tag=v1.18.0 2>&1 | tail -2
echo

# Watch pods cycle
kubectl rollout status statefulset/qdrant -n qdrant --timeout=300s
echo "$(date '+%H:%M:%S') ROLLOUT complete"

# Let the loop run a bit more
sleep 8

# Stop streaming
kill $LOG_PID 2>/dev/null

echo
echo "=== Results ==="
TOTAL=$(wc -l < /tmp/in-cluster.log)
OK=$(awk '$2=="200"' /tmp/in-cluster.log | wc -l)
echo "Total queries: $TOTAL"
echo "HTTP 200    : $OK"
echo "Non-200 codes:"
awk '$2!="200" {print $2}' /tmp/in-cluster.log | sort | uniq -c | sort -rn

echo
echo "First and last 3 lines:"
head -3 /tmp/in-cluster.log
echo "..."
tail -3 /tmp/in-cluster.log

kubectl delete pod query-loop -n qdrant --grace-period=0 --force >/dev/null 2>&1

echo
echo "=== Image now: $(kubectl get statefulset qdrant -n qdrant -o jsonpath='{.spec.template.spec.containers[0].image}') ==="
echo "=== Pod state: ==="
kubectl get pods -n qdrant -o wide
