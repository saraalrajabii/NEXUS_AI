# NEXUS

A custom customer-support workspace built on top of open-source services.
Agents work inside the NEXUS interface; external tools (starting with Chatwoot) run in the background as services.

This repository is also a teaching course — each lesson lives in `docs/lessons/`.

- Architecture: [docs/architecture.md](docs/architecture.md)
- Lesson 01 (in progress): [Foundation + Chatwoot integration](docs/lessons/lesson-01.md)

> Status: **Lesson 01 complete.** All acceptance criteria were met and verified end to end;
> see the [acceptance report](docs/lessons/lesson-01.md#milestone-5--end-to-end-verification).
> Re-check any time with `python3 scripts/e2e_check.py`.
>
> First-time Chatwoot setup (onboarding, token, `scripts/chatwoot_setup.py`) is described in
> [docs/lessons/lesson-01.md](docs/lessons/lesson-01.md#milestone-4--connecting-chatwoot).

## Quick start

1. **Configuration:** `cp .env.example .env`, then set `NEXUS_DB_PASSWORD` in `.env` (generate one with `openssl rand -hex 16`).
2. **Backend and database:**

   ```bash
   docker compose up -d --build
   ```

   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
3. **Frontend:**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Then open http://localhost:5173.

Run the backend tests with `docker compose exec nexus-backend pytest`.

## Deploying

See [docs/deploy/railway.md](docs/deploy/railway.md) for Railway: separate backend and frontend services, a
Railway Postgres database, and a password gate in front of the UI.
