# Install Qdrant on Ubuntu LTS

Companion to: https://computingforgeeks.com/install-qdrant-ubuntu/

Tested on Ubuntu 24.04 LTS. Same steps apply to 22.04 and 26.04.

## Two install paths

```bash
# Docker (recommended for most cases)
./install.sh docker

# Native .deb + systemd
./install.sh native
```

After either path:

```bash
curl -s http://localhost:6333/healthz
# {"title":"qdrant - vector search engine","version":"1.18.x"}
```

Open the Web UI at `http://<server>:6333/dashboard`.

## Files

- [`install.sh`](./install.sh) — installs Docker or the native .deb, sets up storage, starts the service.
- [`qdrant.service`](./qdrant.service) — the systemd unit dropped at `/etc/systemd/system/qdrant.service` by the native path.

## Production posture

This is the bare install. For real workloads add:

- API key + TLS reverse proxy (see `../tls-nginx/` once the security article ships)
- Snapshots to S3 (see `../backup/`)
- Prometheus monitoring (see `../monitoring/`)
