# Deploying NEXUS on Railway

## Why the first deploy failed

Railway's automatic builder (Railpack) looks at the **top folder** of the repo and tries to build one app.
NEXUS is several services in sub-folders (`backend/`, `frontend/`) plus databases. Railpack found no app at
the top and stopped with:

```
✖ Railpack could not determine how to build the app.
```

`docker-compose.yml` is for running everything **locally**; Railway does not run it as-is.
On Railway, each part becomes its own **service**.

## What runs where

```
Internet ──HTTPS──► frontend (Caddy: password gate + serves the React app)
                        │  /api/*, /health/*, /webhooks/*   (Railway private network)
                        ▼
                    backend (FastAPI) ──► Postgres (Railway database)
                        │
                        └──► Chatwoot (optional, see Part 2)
```

- Only the **frontend** gets a public address. The backend and database stay private.
- The frontend asks for a **username and password** (HTTP basic auth). NEXUS has no user accounts yet, so this
  stops strangers reading conversations. If the password hash is missing, the frontend refuses to start.
- `/healthz` (Railway's health check) and `/webhooks/*` (Chatwoot) skip the password. Webhooks are protected
  by their HMAC signature instead.

## Part 1 — NEXUS (backend + frontend + database)

### 1. Database

In the Railway project: **+ Create → Database → PostgreSQL**. Leave the name as `Postgres`.

### 2. Backend service

Use the service that is connected to the GitHub repo. In this course it is called `NEXUS_AI`; if you rename
it (for example to `backend`), change the name inside `BACKEND_URL` in step 3 to match.

**Settings → Source**
- **Root Directory:** `/backend`

**Settings → Deploy → Healthcheck Path:** `/health/live`

Railway builds with `backend/Dockerfile` automatically, because it finds a Dockerfile in the root directory.

> Railway's older "Config as Code" (`railway.json`) can't be turned on for new services any more, so
> everything is set in the dashboard instead.

**Variables:**

| Variable | Value | Why |
|---|---|---|
| `NEXUS_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | A reference: Railway fills in the database address |
| `PORT` | `8000` | A fixed port, so the frontend knows where to find the backend |
| `HOST` | `::` | The default. Listens on IPv6 (Railway's private network) **and** IPv4 (Railway's health checks) |
| `NEXUS_RELOAD` | `false` | No auto-reload in production |
| `LOG_LEVEL` | `info` | |

Don't generate a public domain for the backend.

### 3. Frontend service

**+ Create → GitHub Repo → `NEXUS_AI`** (the same repo again), then rename it to `frontend`.

**Settings → Source → Root Directory:** `/frontend`
**Settings → Deploy → Healthcheck Path:** `/healthz`

**Variables:**

| Variable | Value |
|---|---|
| `BACKEND_URL` | `http://${{NEXUS_AI.RAILWAY_PRIVATE_DOMAIN}}:8000` (use your backend service's name) |
| `NEXUS_UI_USER` | a login name, e.g. `nexus` |
| `NEXUS_UI_PASSWORD_HASH` | the bcrypt hash of your password (see below) |

Create the hash on your computer. Replace `your-password` with your own; only the hash goes to Railway:

```bash
docker run --rm caddy:2.11.8-alpine caddy hash-password --plaintext 'your-password'
```

**Settings → Networking → Generate Domain.** This is the address you open in the browser.

### 4. Check it

1. Both services show **Active / Deployed**.
2. Open the frontend's domain. The browser asks for a username and password.
3. After logging in, the Dashboard shows **NEXUS backend: Connected** and **NEXUS database: Connected**.
   Chatwoot shows **Not configured** until Part 2.
4. In the backend's **Deploy Logs** you should see `Running upgrade -> 0001` once, then
   `[serve] Listening on port 8000 (IPv4+IPv6)`.

## Part 2 — Chatwoot (optional)

NEXUS works without Chatwoot, but the Inbox stays empty. Chatwoot needs four more services (web, worker,
Postgres **with pgvector**, Redis), and on the Trial plan that can use up the credit quickly. Options:

- **Use an existing Chatwoot** (for example Chatwoot Cloud or another server). Set these on the backend:
  `CHATWOOT_BASE_URL`, `CHATWOOT_ACCOUNT_ID`, `CHATWOOT_API_TOKEN`. Then run the setup script against it.
  Set the webhook URL to `https://<frontend-domain>/webhooks/chatwoot`.
- **Run Chatwoot on Railway** with Railway's Chatwoot template. Then connect it the same way.

Either way, add `CHATWOOT_WEBHOOK_SECRET` to the backend once the webhook exists.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Railpack could not determine how to build the app` | Root Directory not set | Set it to `/backend` or `/frontend` |
| Build uses Railpack instead of the Dockerfile | Root Directory doesn't point at the folder with the Dockerfile | Set Root Directory to `/backend` or `/frontend` |
| Backend stuck on "Deploying", then fails its health check | The server listened on IPv6 only, and Railway health-checks over IPv4 | Fixed in `app/serve.py` (one socket for both). Make sure the healthcheck path is `/health/live` |
| Frontend crashes: `username and password cannot be empty` | `NEXUS_UI_PASSWORD_HASH` missing | Add the hash (step 3). This is intentional: it never starts without a password |
| Logged in, but every panel says *Backend not reachable* | Wrong `BACKEND_URL` | `BACKEND_URL=http://${{<backend service name>.RAILWAY_PRIVATE_DOMAIN}}:8000`, with `PORT=8000` on the backend |
| Backend health check fails | Database not connected | Check `NEXUS_DATABASE_URL=${{Postgres.DATABASE_URL}}` and that the Postgres service is running |
