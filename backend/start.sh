#!/bin/sh
# Container start-up: bring the database schema up to date, then start the API server.
#   PORT  – port to listen on. Hosting platforms (e.g. Railway) set this; default 8000.
#   HOST  – address to bind. Default 0.0.0.0 (IPv4). Use "::" where private networking is IPv6 (Railway).
set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "[start] Applying database migrations (alembic upgrade head)…"
alembic upgrade head

if [ "${NEXUS_RELOAD:-false}" = "true" ]; then
  echo "[start] Starting API on ${HOST}:${PORT} with auto-reload (development mode)"
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload --reload-dir app
else
  echo "[start] Starting API on ${HOST}:${PORT}"
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --proxy-headers --forwarded-allow-ips='*'
fi
