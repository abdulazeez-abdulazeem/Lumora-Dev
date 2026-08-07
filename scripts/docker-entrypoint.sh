#!/bin/sh
set -e
API_PORT="${PORT:-8000}"
export LUMORA_BIND="${LUMORA_BIND:-0.0.0.0}"
export LUMORA_API_PORT="$API_PORT"
export LUMORA_FRONTEND_PORT="${LUMORA_FRONTEND_PORT:-${FRONTEND_PORT:-5000}}"

echo "Lumora entrypoint: API on ${LUMORA_BIND}:${API_PORT}"

# Primary public process (Pxxl/Render/Railway/Koyeb/Northflank map this PORT)
exec uvicorn backend.api:app --host "${LUMORA_BIND}" --port "$API_PORT"
