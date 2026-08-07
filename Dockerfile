# Lumora Dev v4.0 — production container (API + frontend proxy)
# Architecture unchanged: FastAPI (backend.api) + server.py static proxy

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LUMORA_BIND=0.0.0.0 \
    PORT=8000 \
    FRONTEND_PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional Playwright (uncomment if needed in cloud):
# RUN pip install playwright && playwright install --with-deps chromium

COPY . .
RUN rm -f .env .lumora-secret.key .lumora-auth.json 2>/dev/null || true

EXPOSE 8000 5000

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/system/health" || curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
