#!/usr/bin/env bash
set -euo pipefail

# Top-level installer & runner for dev/test environments. Run from repo root.
# Usage: ./scripts/install_and_run.sh [--no-compose]

NO_COMPOSE=0
if [[ "${1:-}" == "--no-compose" ]]; then
  NO_COMPOSE=1
fi

echo "=== Install & Run Script ==="

# 1) Ensure Python venv and deps
echo "[1/5] Creating Python venv and installing requirements..."
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2) Build Kali image
echo "[2/5] Building Kali sandbox image..."
./scripts/build_kali.sh kali-linux-headless:latest

# 3) Create internal sandbox network
if ! docker network inspect pentest-sandbox-net >/dev/null 2>&1; then
  echo "[3/5] Creating internal docker network pentest-sandbox-net..."
  docker network create --internal --driver bridge pentest-sandbox-net || true
else
  echo "[3/5] Sandbox network already exists."
fi

# 4) Start backend (docker compose or local uvicorn)
if [[ "$NO_COMPOSE" -eq 0 && -f docker-compose.sandbox.yml ]]; then
  echo "[4/5] Starting docker-compose stack..."
  docker compose -f docker-compose.sandbox.yml up --build -d
  echo "Waiting for backend to initialize..."
  sleep 3
else
  echo "[4/5] Running backend locally with uvicorn in background..."
  # Start uvicorn in background (adjust module if different)
  nohup .venv/bin/uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000 > backend_uvicorn.log 2>&1 &
  sleep 1
fi

# 5) Trigger a safe example scan and show how to connect to WS
echo "[5/5] Triggering example scan and printing WS URL..."
python - <<'PY'
import requests, time
try:
    resp = requests.post('http://localhost:8000/api/v1/scan', json={'session_id':'install-run-test','command':'echo hello-from-sandbox && sleep 1 && echo finished'})
    print('Scan POST status:', resp.status_code)
except Exception as e:
    print('Could not POST scan:', e)
PY

echo "Connect to the websocket logs at: ws://localhost:8000/ws/sessions/install-run-test/logs"

echo "Installation and run steps completed. Check backend logs or the websocket output." 
