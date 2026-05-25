#!/usr/bin/env bash
# Install Qdrant on Rocky Linux 10 / AlmaLinux 10 via Docker CE.
# Companion to: https://computingforgeeks.com/install-qdrant-rocky-linux/
#
# Handles the real gotcha most fresh Rocky 10 cloud images hit:
# the kernel-modules-extra-matched package installed alongside docker-ce
# pulls modules for a NEWER kernel than the one currently running, so the
# Docker daemon fails to add its nftables rules. Fix: install the matching
# kernel, reboot, then start the daemon.
set -euo pipefail

echo "==> Installing Docker CE"
sudo dnf -y install dnf-plugins-core curl jq
sudo dnf config-manager --add-repo \
  https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

RUNNING_KERNEL=$(uname -r)
MATCHED_MODULES=$(rpm -qa | grep -E '^kernel-modules-extra-matched-' | head -1)
MATCHED_KERNEL=${MATCHED_MODULES#kernel-modules-extra-matched-}

if [[ -n "$MATCHED_KERNEL" && "$MATCHED_KERNEL" != "$RUNNING_KERNEL" ]]; then
  echo "==> Kernel mismatch detected"
  echo "    running:  $RUNNING_KERNEL"
  echo "    expected: $MATCHED_KERNEL"
  echo "==> Installing matching kernel and rebooting"
  sudo dnf -y install kernel kernel-core kernel-modules kernel-modules-core
  echo
  echo "Reboot required. Run: sudo shutdown -r now"
  echo "After reboot, re-run this script to finish the install."
  exit 0
fi

echo "==> Enabling Docker"
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

echo "==> Pulling Qdrant"
QDRANT_VERSION="${QDRANT_VERSION:-$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | jq -r .tag_name)}"
sudo docker pull "qdrant/qdrant:${QDRANT_VERSION}"

echo "==> Starting Qdrant container"
sudo mkdir -p /var/lib/qdrant/storage
if sudo docker ps -a --format '{{.Names}}' | grep -q '^qdrant$'; then
  sudo docker rm -f qdrant
fi
sudo docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 -p 6334:6334 \
  -v /var/lib/qdrant/storage:/qdrant/storage:z \
  "qdrant/qdrant:${QDRANT_VERSION}"

echo "==> Waiting for health"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:6333/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done

echo
echo "OK. REST: http://localhost:6333  |  Web UI: http://localhost:6333/dashboard"
echo "Storage: /var/lib/qdrant/storage"
echo
echo "If firewalld is enabled, open the ports:"
echo "  sudo firewall-cmd --permanent --add-port=6333/tcp"
echo "  sudo firewall-cmd --permanent --add-port=6334/tcp"
echo "  sudo firewall-cmd --reload"
echo "  sudo systemctl restart docker   # firewalld reload wipes Docker's nftables rules"
