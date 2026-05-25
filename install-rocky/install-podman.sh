#!/usr/bin/env bash
# Install Qdrant via rootless Podman on Rocky Linux 10 / AlmaLinux 10.
# Companion to: https://computingforgeeks.com/install-qdrant-rocky-linux/
#
# Rootless Podman needs TWO mount labels for a bind mount to work under
# SELinux enforcing:
#   :z   relabel host directory to container_file_t
#   :U   chown to the user-namespace UID Podman maps inside the container
# Without :U you get "Permission denied (os error 13)" from Qdrant.
set -euo pipefail

echo "==> Installing Podman"
sudo dnf -y install podman curl jq
podman --version

QDRANT_VERSION="${QDRANT_VERSION:-$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | jq -r .tag_name)}"
STORAGE_DIR="${STORAGE_DIR:-${HOME}/qdrant-storage}"

mkdir -p "$STORAGE_DIR"

if podman ps -a --format '{{.Names}}' | grep -q '^qdrant$'; then
  podman rm -f qdrant
fi

echo "==> Starting rootless Qdrant"
podman run -d \
  --name qdrant \
  --restart=unless-stopped \
  -p 6333:6333 -p 6334:6334 \
  -v "${STORAGE_DIR}:/qdrant/storage:z,U" \
  "docker.io/qdrant/qdrant:${QDRANT_VERSION}"

echo "==> Waiting for health"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done

echo
echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
echo "Storage: ${STORAGE_DIR}"
echo
echo "For a systemd-managed rootless service, generate a Quadlet unit at:"
echo "  ~/.config/containers/systemd/qdrant.container"
echo "See ./qdrant.container in this directory for a working template."
