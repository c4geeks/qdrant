# Multi-node Qdrant Cluster on Kubernetes

Companion to: https://computingforgeeks.com/qdrant-kubernetes-cluster/

A real 3-node Qdrant 1.18.1 cluster on a Kubernetes StatefulSet via the
official Helm chart, with HA proven via force-delete + rolling upgrade
zero-downtime experiments.

## Files

| File | Purpose |
|---|---|
| `values.yaml` | Helm values: 3 replicas, cluster=on, antiAffinity, 4Gi PVC, api-key |
| `install.sh` | Add repo, install/upgrade chart, wait for rollout, smoke-test raft |
| `cluster_workload.py` | Create sharded+replicated collection (shard=6, rf=2), seed 5000 BGE points |
| `failure_test.sh` | Continuous query loop + force-delete a pod, count zero-downtime responses |
| `rolling_upgrade_test.sh` | In-cluster query loop + helm upgrade image tag, count zero-downtime |

## Quick start

```bash
# Pre-req: a Kubernetes cluster with a default StorageClass + 3 schedulable nodes
kubectl get nodes
# k3s ships with local-path; EKS: swap to gp3 in values.yaml; GKE: pd-standard

./install.sh
# Watches the rollout, then prints the raft state of the cluster
```

## Measured results (k3s v1.35.5 / 3 × 4-vCPU/4GB VMs / Qdrant 1.18.1)

| Operation | Result |
|---|---|
| Helm install rollout | ~60 s for 3 pods Ready |
| Raft consensus after bootstrap | term=1, 3 peers, leader elected |
| Collection (shard=6, rf=2) | 12 shard-replicas, 4 per pod |
| 5000 BGE-small upsert (write_consistency=2) | 2.6 s after embed time |
| Force-delete pod under load | 60/60 queries OK, pod restored in ~8 s |
| Rolling upgrade v1.18.1 → v1.18.0 | 128/128 queries OK, rollout 64 s |

## Gotchas these scripts catch

- Distroless image has no `curl`. Use `kubectl run --image=curlimages/curl`
  for in-cluster probes.
- `kubectl port-forward svc/qdrant` attaches to one pod; tunnel breaks when
  that pod is killed. Use an Ingress/LB for real client traffic, or run the
  probe loop in-cluster.
- qdrant-1 restarts twice on first cluster bootstrap. Normal behaviour, not
  a bug. Wait for it.
- New peers added via `replicaCount` do not auto-rebalance existing shards.
  Use the `move_shard` cluster API explicitly.
- `local-path` PVCs are pinned to a node. On bare-metal use Longhorn,
  OpenEBS, or Rook-Ceph for portable PVCs.

Tested 2026-05 on Ubuntu 24.04 VMs (Proxmox) with k3s v1.35.5,
qdrant Helm chart v1.18.0 (App Version v1.18.1).
