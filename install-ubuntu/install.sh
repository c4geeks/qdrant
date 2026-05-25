#!/usr/bin/env bash
# Install Qdrant on Ubuntu 26.04 / 24.04 / 22.04 LTS.
# Companion to: https://computingforgeeks.com/install-qdrant-ubuntu/
# Two modes: docker (default) or native deb install.
set -euo pipefail

MODE="${1:-docker}"

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required" >&2
  exit 1
fi

case "$MODE" in
  docker)
    echo "==> Installing Docker engine"
    if ! command -v docker >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y ca-certificates curl
      sudo install -m 0755 -d /etc/apt/keyrings
      sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
      sudo chmod a+r /etc/apt/keyrings/docker.asc
      . /etc/os-release
      echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
        https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
      sudo apt-get update -y
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
      sudo usermod -aG docker "$USER" || true
    fi

    echo "==> Pulling and starting Qdrant"
    sudo mkdir -p /var/lib/qdrant/storage
    sudo docker run -d \
      --name qdrant \
      --restart unless-stopped \
      -p 6333:6333 -p 6334:6334 \
      -v /var/lib/qdrant/storage:/qdrant/storage:z \
      qdrant/qdrant

    echo "==> Waiting for health..."
    for _ in $(seq 1 30); do
      if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done

    echo
    echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
    ;;

  native)
    echo "==> Detecting latest Qdrant release"
    QDRANT_VERSION="${QDRANT_VERSION:-$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | grep -oP '"tag_name":\s*"\K[^"]+')}"
    QDRANT_PKG_VERSION="${QDRANT_VERSION#v}"

    echo "==> Installing Qdrant ${QDRANT_VERSION}"
    cd /tmp
    curl -fL --retry 3 -o "qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb" \
      "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb"  # https://github.com/qdrant/qdrant/releases
    sudo apt-get install -y "./qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb"

    echo "==> Creating system user and storage directories"
    if ! id qdrant >/dev/null 2>&1; then
      sudo useradd -r -s /sbin/nologin qdrant
    fi
    sudo mkdir -p /var/lib/qdrant/storage /etc/qdrant
    sudo chown -R qdrant:qdrant /var/lib/qdrant

    echo "==> Installing systemd unit"
    sudo tee /etc/systemd/system/qdrant.service >/dev/null <<'UNIT'
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
WorkingDirectory=/var/lib/qdrant
ExecStart=/usr/bin/qdrant
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
UNIT

    sudo systemctl daemon-reload
    sudo systemctl enable --now qdrant

    echo "==> Waiting for health..."
    for _ in $(seq 1 30); do
      if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done

    echo
    echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
    ;;

  *)
    echo "Usage: $0 [docker|native]" >&2
    exit 1
    ;;
esac
