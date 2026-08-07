#!/bin/sh
set -e
API_PORT="${PORT:-8000}"
export LUMORA_BIND="${LUMORA_BIND:-0.0.0.0}"

uvicorn backend.api:app --host 0.0.0.0 --port "$API_PORT" &
API_PID=$!

if [ "$API_PORT" != "8000" ]; then
  echo "Note: server.py proxies to fixed port 8000; set PORT=8000 for dual-process UI, or use API-only."
fi
python server.py &
UI_PID=$!

term() {
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
  wait "$API_PID" "$UI_PID" 2>/dev/null || true
}
trap term TERM INT

wait "$API_PID"
