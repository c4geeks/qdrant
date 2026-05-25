#!/usr/bin/env bash
# Install Qdrant on Debian 13 (Trixie) or Debian 12 (Bookworm) via Docker CE.
# Includes journald log forwarding so container logs land in `journalctl`.
# Companion to: https://computingforgeeks.com/install-qdrant-debian/
set -euo pipefail

echo "==> Installing prerequisites"
sudo apt-get update -qq
sudo apt-get install -y ca-certificates curl jq

echo "==> Adding Docker CE repo"
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update -qq
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER" || true

echo "==> Configuring journald log driver"
sudo mkdir -p /etc/docker
echo '{"log-driver":"journald"}' | sudo tee /etc/docker/daemon.json >/dev/null
sudo systemctl restart docker

echo "==> Pulling and starting Qdrant"
QDRANT_VERSION="${QDRANT_VERSION:-$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | jq -r .tag_name)}"
sudo mkdir -p /var/lib/qdrant/storage
if sudo docker ps -a --format '{{.Names}}' | grep -q '^qdrant$'; then
  sudo docker rm -f qdrant
fi
sudo docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 -p 6334:6334 \
  -v /var/lib/qdrant/storage:/qdrant/storage \
  "qdrant/qdrant:${QDRANT_VERSION}"

echo "==> Waiting for health"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done

echo
echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
echo "Logs:  sudo journalctl CONTAINER_NAME=qdrant -f"
