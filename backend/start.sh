#!/bin/sh
# Container start-up: bring the database schema up to date, then start the API server.
set -e

echo "[start] Applying database migrations (alembic upgrade head)…"
alembic upgrade head

if [ "${NEXUS_RELOAD:-false}" = "true" ]; then
  echo "[start] Starting API with auto-reload (development mode)"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
else
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
