#!/usr/bin/env bash
set -euo pipefail
IMAGE_NAME="${1:-kali-linux-headless:latest}"
DOCKERFILE="${2:-Dockerfile.kali}"

echo "Building Kali sandbox image: ${IMAGE_NAME} (Dockerfile: ${DOCKERFILE})"
docker build -f "${DOCKERFILE}" -t "${IMAGE_NAME}" .
echo "Done. To use this image set SANDBOX_IMAGE=${IMAGE_NAME}"
