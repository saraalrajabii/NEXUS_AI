#!/bin/sh
# Container start-up: bring the database schema up to date, then start the API server.
#   PORT  – port to listen on. Hosting platforms (e.g. Railway) set this; default 8000.
#   HOST  – production only: "::" (default) listens on IPv4 AND IPv6; "0.0.0.0" = IPv4 only.
set -e

echo "[start] Applying database migrations (alembic upgrade head)…"
alembic upgrade head

if [ "${NEXUS_RELOAD:-false}" = "true" ]; then
  echo "[start] Development mode: auto-reload on port ${PORT:-8000}"
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload --reload-dir app
else
  echo "[start] Production mode"
  exec python -m app.serve
fi
