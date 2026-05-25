# Qdrant Mastery — Companion Code

Tested, working code for the [Computing for Geeks](https://computingforgeeks.com) **Qdrant Vector Database** article series. Every directory in this repo maps to one article. Everything here has been tested end-to-end on Proxmox VMs (Ubuntu 26.04 / 24.04, Rocky Linux 10, Debian 13), and where GPU is involved, on vast.ai RTX 4090 instances.

Qdrant version pinned to **v1.18.x** unless noted. Where you see `${QDRANT_VERSION}` in a script, detect the latest with:

```bash
export QDRANT_VERSION=$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | jq -r .tag_name)
```

## Article Index

| # | Article | Directory |
|---|---|---|
| 1 | Qdrant Vector Database: Complete Guide for 2026 (pillar) | [`pillar/`](./pillar) |
| 2 | Install Qdrant on Ubuntu 26.04 / 24.04 LTS | [`install-ubuntu/`](./install-ubuntu) |
| 3 | Install Qdrant on Rocky Linux 10 / AlmaLinux 10 | [`install-rocky/`](./install-rocky) |
| 4 | Install Qdrant on Debian 13 / 12 | [`install-debian/`](./install-debian) |
| 5 | Qdrant Web UI Tour | [`web-ui-demo/`](./web-ui-demo) |
| 6 | Qdrant Collections | [`collections/`](./collections) |
| 7 | Qdrant REST and gRPC APIs | [`api/`](./api) |
| 8 | Qdrant Filters and Payload Indexes | [`filters/`](./filters) |
| 9 | Secure Qdrant with API Key, TLS, and Nginx | [`tls-nginx/`](./tls-nginx) |
| 10 | Qdrant JWT + RBAC | [`jwt-rbac/`](./jwt-rbac) |
| 11 | Qdrant Snapshots: Backup, Restore, S3 | [`backup/`](./backup) |
| 12 | Monitor Qdrant with Prometheus + Grafana | [`monitoring/`](./monitoring) |
| 13 | Qdrant 3-Node Distributed Cluster | [`docker/cluster-3-node/`](./docker/cluster-3-node) |
| 14 | Qdrant on Kubernetes with Helm | [`kubernetes/`](./kubernetes) |
| 15 | Performance Tuning + Quantization | [`benchmarks/`](./benchmarks) |
| 16 | GPU Acceleration on vast.ai | [`gpu/`](./gpu) |
| 17 | Local RAG with Qdrant + Ollama + LangChain | [`rag-langchain/`](./rag-langchain) |
| 18 | PDF Q&A RAG with Qdrant + LlamaIndex | [`rag-llamaindex/`](./rag-llamaindex) |
| 19 | Visual Image Search with Qdrant + CLIP | [`image-search/`](./image-search) |
| 20 | Semantic Search API with Qdrant + FastAPI | [`semantic-api/`](./semantic-api) |
| 21 | Qdrant + n8n No-Code Workflows | [`n8n/`](./n8n) |
| 22 | Qdrant vs pgvector vs Milvus vs Weaviate Benchmark | [`benchmarks-vs-others/`](./benchmarks-vs-others) |
| 23 | Migrate from Pinecone to Qdrant | [`migration/`](./migration) |
| 24 | Qdrant Commands + API Cheat Sheet | [`cheatsheet/`](./cheatsheet) |

Shared infrastructure:

- [`docker/single-node/`](./docker/single-node) — base Docker Compose for any single-node article
- [`docker/tls-nginx/`](./docker/tls-nginx) — Nginx + TLS reverse proxy
- [`config/`](./config) — reusable `config.yaml` profiles (production, TLS, S3 snapshots)
- [`terraform/`](./terraform) — OpenTofu / Terraform module for AWS EC2 and GCP GCE

## Quick Try (60 seconds)

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
  qdrant/qdrant
open http://localhost:6333/dashboard
```

That gets you a running Qdrant with the Web UI. For anything production, start with [`docker/single-node/`](./docker/single-node) and add TLS + auth from [`tls-nginx/`](./tls-nginx) + [`jwt-rbac/`](./jwt-rbac).

## Test Infrastructure

- **Proxmox lab** (primary): single-node and cluster articles on Ubuntu 26.04 / 24.04, Rocky 10, Debian 13
- **vast.ai RTX 4090** (~$0.50/hr): GPU acceleration article (16); optional burst for benchmarks (15, 22) and bulk image embedding (19)
- **AWS + GCP**: Terraform module validation (`terraform/aws-ec2/`, `terraform/gcp-gce/`)

## License

MIT. See [LICENSE](./LICENSE).

## Contributing

Issues and PRs welcome. Open an issue if any command in this repo does not reproduce the article's results on a clean Proxmox VM or vast.ai instance.
