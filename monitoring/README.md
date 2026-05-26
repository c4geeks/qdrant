# Monitoring Qdrant with Prometheus and Grafana

Companion to: https://computingforgeeks.com/qdrant-prometheus-grafana/

End-to-end observability for a 3-node Qdrant cluster on Kubernetes:
kube-prometheus-stack with a slim values file, a ServiceMonitor on the
Qdrant chart, a Grafana dashboard provisioned via the API, and five
PrometheusRule alerts with one verified firing.

## Files

| File | Purpose |
|---|---|
| `kps-values.yaml` | Lightweight kube-prometheus-stack values for a 3 × 4 GB lab |
| `qdrant-values.yaml` | Qdrant chart values with `metrics.serviceMonitor.enabled=true` |
| `qdrant-alerts.yaml` | 5 PrometheusRule alerts (peer count, target down, latency, dead replicas, raft backlog) |
| `qdrant-dashboard.json` | Grafana dashboard JSON: 6 stat panels + 4 time-series |
| `provision-dashboard.sh` | Discover Prometheus DS UID, patch JSON, POST to `/api/dashboards/db` |
| `seed_and_load.py` | Seed 5 000 BGE-small embeddings + drive sustained query load for dashboard data |

## Order matters

Install kube-prometheus-stack FIRST so the `ServiceMonitor` CRD exists when the Qdrant chart references it:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add qdrant               https://qdrant.github.io/qdrant-helm
helm repo update

kubectl create namespace monitoring
helm install kps prometheus-community/kube-prometheus-stack \
    -n monitoring -f kps-values.yaml

# Wait for Prometheus, AlertManager, and Grafana to all reach Ready
kubectl get pods -n monitoring | grep -E "(prometheus|grafana|alertmanager)"

kubectl create namespace qdrant
helm install qdrant qdrant/qdrant -n qdrant -f qdrant-values.yaml

kubectl apply -f qdrant-alerts.yaml
bash provision-dashboard.sh
```

## Drill the alert

```bash
# Trigger QdrantPeerCountBelowExpected
kubectl scale statefulset qdrant -n qdrant --replicas=1
sleep 95   # for: 1m + scrape interval

curl -sS http://localhost:9090/api/v1/alerts | \
    jq '.data.alerts[] | select(.labels.alertname | startswith("Qdrant"))'

# Recover
kubectl scale statefulset qdrant -n qdrant --replicas=3
```

## Gotchas

- Install kube-prometheus-stack BEFORE Qdrant with serviceMonitor enabled.
  The Qdrant chart references the `ServiceMonitor` CRD at install time.
- `serviceMonitorSelectorNilUsesHelmValues: false` (and matching podMonitor +
  rule flags) is what makes the operator pick up resources outside its own
  namespace.
- `up == 0` does not fire when a pod is deleted; the target disappears
  entirely. Use `count(up{job="..."}) < expected` instead.
- Grafana datasource UIDs are generated, not fixed. Discover via API before
  importing a dashboard JSON across clusters.
- kube-prometheus-stack ships dozens of preset alerts that fire on a
  vanilla k3s install (`KubeControllerManagerDown`, `KubeSchedulerDown`,
  `KubeProxyDown`) because k3s embeds those components in the k3s binary.
  Silence them in AlertManager rather than removing them.

Tested 2026-05 on k3s v1.35.5 / 3 × 4-vCPU/4GB Proxmox VMs with Qdrant
chart 1.18.0 (App Version v1.18.1) + kube-prometheus-stack 85.3.3.
