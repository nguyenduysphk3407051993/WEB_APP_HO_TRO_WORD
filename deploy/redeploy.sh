#!/usr/bin/env bash
# Rebuild và restart containers sau khi cập nhật code.
# Chạy tại thư mục dự án: bash deploy/redeploy.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "[redeploy] Pulling latest images (nếu có)..."
docker compose pull --ignore-pull-failures || true

echo "[redeploy] Building..."
docker compose build

echo "[redeploy] Restarting..."
docker compose up -d

echo "[redeploy] Trạng thái:"
docker compose ps

echo "[redeploy] Logs (Ctrl+C để thoát)..."
docker compose logs -f --tail=50
