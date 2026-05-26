#!/usr/bin/env bash
# Set up the local RAG stack on a fresh CUDA-capable Linux box.
# Idempotent - re-running just upgrades the Python deps.
set -euo pipefail

# 1. System packages
apt-get update -y
apt-get install -y --no-install-recommends \
  curl ca-certificates git jq build-essential \
  python3 python3-venv python3-pip lsb-release

# 2. Ollama
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Ollama serves on 127.0.0.1:11434 by default; ensure it is running.
if ! pgrep -x ollama >/dev/null; then
  nohup ollama serve > /var/log/ollama.log 2>&1 &
  sleep 5
fi

# 3. Models
ollama pull nomic-embed-text
ollama pull llama3.1:8b

# 4. Qdrant - run as a plain container is the easy path; if Docker is not
#    available, fall back to the standalone binary release.
mkdir -p /opt/qdrant /opt/qdrant/storage /opt/qdrant/snapshots

QDRANT_VERSION="${QDRANT_VERSION:-v1.18.1}" #https://github.com/qdrant/qdrant/releases

if [ ! -x /usr/local/bin/qdrant ]; then
  cd /tmp
  curl -fsSL -o qdrant.tar.gz \
    "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-gnu.tar.gz"
  tar -xzf qdrant.tar.gz
  install -m 0755 qdrant /usr/local/bin/qdrant
fi

if [ ! -d /opt/qdrant/static ]; then
  cd /tmp
  curl -fsSL -o dashboard.tar.gz \
    "https://github.com/qdrant/qdrant-web-ui/releases/latest/download/dist-qdrant.tar.gz" || true
  if [ -s dashboard.tar.gz ]; then
    mkdir -p /opt/qdrant/static
    tar -xzf dashboard.tar.gz -C /opt/qdrant/static --strip-components=1
  fi
fi

cat >/opt/qdrant/config.yaml <<'YAML'
service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  enable_cors: true
storage:
  storage_path: /opt/qdrant/storage
  snapshots_path: /opt/qdrant/snapshots
log_level: INFO
YAML

# Start Qdrant under a simple supervisor (no systemd in containers)
if ! pgrep -x qdrant >/dev/null; then
  nohup /usr/local/bin/qdrant --config-path /opt/qdrant/config.yaml \
    > /var/log/qdrant.log 2>&1 &
  sleep 3
fi

# 5. Python venv
python3 -m venv /opt/rag/venv
# shellcheck disable=SC1091
source /opt/rag/venv/bin/activate
pip install --upgrade pip
pip install -r "$(dirname "$0")/requirements.txt"

echo
echo "=== ready ==="
curl -s http://127.0.0.1:11434/api/tags | jq '.models[].name'
curl -s http://127.0.0.1:6333/ | jq '{title, version}'
