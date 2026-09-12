#!/usr/bin/env bash
# Second Brain Command Center — unified local launcher (Phase 1, READ-ONLY)
# Starts the thin BFF + the Vite dev server. No daemon authority is created.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_PORT="${SBC_API_PORT:-8790}"
WEB_PORT="${SBC_WEB_PORT:-5173}"

# Resolve a python interpreter (venv preferred, then managed, then system).
PY=""
for cand in \
  "$HERE/api/.venv/Scripts/python.exe" \
  "$HERE/api/.venv/bin/python" \
  "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  "$(command -v python3 || true)" \
  "$(command -v python || true)"; do
  if [ -n "$cand" ] && [ -f "$cand" ]; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then echo "ERROR: no python interpreter found"; exit 1; fi

echo "[1/2] installing backend deps (if needed)..."
"$PY" -m pip install -q -r "$HERE/api/requirements.txt" || true

echo "[2/2] starting BFF on :$API_PORT ..."
( cd "$HERE/api" && "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" ) &
API_PID=$!
trap 'echo "stopping BFF ($API_PID)"; kill $API_PID 2>/dev/null || true' EXIT

echo "waiting for BFF..."
for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then echo "BFF OK"; break; fi
  sleep 1
done

echo "starting frontend on :$WEB_PORT ..."
cd "$HERE"
[ -d node_modules ] || npm install
npm run dev
