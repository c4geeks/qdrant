#!/usr/bin/env bash
# Install Qdrant on Debian via the official .deb + a hand-written systemd unit.
# The .deb installs the binary + config but NOT a unit, NOT a user,
# NOT the snapshots directory. This script creates all three.
# Companion to: https://computingforgeeks.com/install-qdrant-debian/
set -euo pipefail

sudo apt-get update -qq
sudo apt-get install -y curl jq

QDRANT_VERSION="${QDRANT_VERSION:-$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | jq -r .tag_name)}"
QDRANT_PKG_VERSION="${QDRANT_VERSION#v}"

echo "==> Downloading Qdrant ${QDRANT_VERSION}"
cd /tmp
curl -fL --retry 3 -o "qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb" \
  "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb"  # https://github.com/qdrant/qdrant/releases

echo "==> Installing .deb"
sudo apt-get install -y "./qdrant_${QDRANT_PKG_VERSION}-1_amd64.deb"
qdrant --version

echo "==> Creating system user + storage + snapshots directories"
if ! id qdrant >/dev/null 2>&1; then
  sudo useradd -r -s /usr/sbin/nologin qdrant
fi
sudo mkdir -p /var/lib/qdrant/storage /var/lib/qdrant/snapshots
sudo chown -R qdrant:qdrant /var/lib/qdrant

echo "==> Writing systemd unit"
sudo tee /etc/systemd/system/qdrant.service >/dev/null <<'EOF'
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
WorkingDirectory=/var/lib/qdrant
ExecStart=/usr/bin/qdrant --config-path /etc/qdrant/config.yaml
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now qdrant

echo "==> Waiting for health"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done

echo
sudo systemctl is-active qdrant
echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
echo "Logs:  sudo journalctl -u qdrant -f"
