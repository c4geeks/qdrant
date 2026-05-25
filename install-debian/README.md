# Install Qdrant on Debian 13 / 12

Companion to: https://computingforgeeks.com/install-qdrant-debian/

Tested on **Debian 13.5 (Trixie)** with kernel `6.12.74+deb13+1-cloud-amd64`. Same steps apply to Debian 12 (Bookworm) since both share apt.

## Two install paths

```bash
# Docker CE with journald log forwarding (recommended)
./install-docker.sh

# Native .deb + hand-written systemd unit
./install-native.sh
```

After either, verify:

```bash
curl -s http://localhost:6333/healthz       # healthz check passed
sudo journalctl CONTAINER_NAME=qdrant -n 5  # for Docker
sudo journalctl -u qdrant -n 5              # for native systemd
```

## Files

- [`install-docker.sh`](./install-docker.sh) — Docker CE install, configures journald driver in `/etc/docker/daemon.json` before first run.
- [`install-native.sh`](./install-native.sh) — Downloads the .deb, creates the `qdrant` system user + storage + snapshots dirs + systemd unit. None of those are shipped by the package.
- [`docker-compose.yml`](./docker-compose.yml) — Production-ready Compose file with API key, memory limit, healthcheck, journald driver.
- [`qdrant.service`](./qdrant.service) — Standalone systemd unit, drop at `/etc/systemd/system/qdrant.service`.

## Real gotchas this catches

1. **The Qdrant .deb ships no systemd unit, no user, no snapshots directory.** Skip any of those three and you get a panic on first start. `install-native.sh` provisions all three.
2. **Docker's journald log driver is per-container at create time**. Setting `/etc/docker/daemon.json` does not retroactively flip existing containers; they need a recreate to pick it up. `install-docker.sh` configures the driver before the first run.
3. **The .deb default config uses absolute path `/var/lib/qdrant/storage`** regardless of `WorkingDirectory` in the unit. If you reuse a directory created by a prior Docker run (root-owned files), the systemd `qdrant` user will hit `PermissionDenied` on the WAL.

## Production posture

This is the bare install. For real workloads add:

- API key + TLS reverse proxy (see `../tls-nginx/` once the security article ships)
- Snapshots to S3 (see `../backup/`)
- Prometheus monitoring (see `../monitoring/`)
