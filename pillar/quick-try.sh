#!/usr/bin/env bash
# Spin a single Qdrant container with the Web UI exposed.
# Companion to: https://computingforgeeks.com/qdrant-vector-database-guide/
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-qdrant}"
STORAGE_DIR="${STORAGE_DIR:-$(pwd)/qdrant_storage}"
REST_PORT="${REST_PORT:-6333}"
GRPC_PORT="${GRPC_PORT:-6334}"
IMAGE="${IMAGE:-qdrant/qdrant}"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Container ${CONTAINER_NAME} already exists. Remove with: docker rm -f ${CONTAINER_NAME}"
  exit 1
fi

mkdir -p "${STORAGE_DIR}"

docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${REST_PORT}:6333" \
  -p "${GRPC_PORT}:6334" \
  -v "${STORAGE_DIR}:/qdrant/storage:z" \
  "${IMAGE}"

echo
echo "Qdrant is starting. Give it a few seconds, then open:"
echo "  REST API:  http://localhost:${REST_PORT}"
echo "  Web UI:    http://localhost:${REST_PORT}/dashboard"
echo "  gRPC:      localhost:${GRPC_PORT}"
echo
echo "Health:"
echo "  curl -s http://localhost:${REST_PORT}/healthz"
echo
echo "Stop and remove:"
echo "  docker rm -f ${CONTAINER_NAME} && rm -rf ${STORAGE_DIR}"
