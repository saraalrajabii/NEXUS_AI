# NEXUS Architecture (Lesson 01)

This document is the approved Milestone 1 design. Later milestones implement it; if the implementation
has to deviate, this file is updated in the same change.

## 1. Goal of Lesson 01

One working end-to-end flow:

```
Customer message → Chatwoot → NEXUS Backend → NEXUS Inbox → Agent reply → Chatwoot
```

## 2. Components and why they exist

| Component | Problem it solves | Why this technology | Talks to |
|---|---|---|---|
| **Frontend** (React + TypeScript + Vite + Tailwind) | Gives agents one interface that we design and own | React is the most widely taught UI library; TypeScript catches mistakes early; Vite starts instantly; Tailwind keeps styling in one place | NEXUS Backend only (via `/api`) |
| **NEXUS Backend** (FastAPI, Python 3.12) | One place for business logic, credentials and data conversion | FastAPI is small, typed, and generates API docs automatically (`/docs`) | Frontend, NEXUS DB, Chatwoot REST API; receives Chatwoot webhooks |
| **Integration adapter** (`backend/app/integrations/chatwoot/`) | Isolates everything Chatwoot-specific so the rest of NEXUS never sees Chatwoot's data shapes | A plain Python package: client + signature check + mapper | Chatwoot REST API |
| **NEXUS DB** (PostgreSQL 17) | Stores NEXUS's own data: events, conversations, messages | Reliable, free, and has unique constraints we use for de-duplication | NEXUS Backend only |
| **Chatwoot** (official image v4.19.1 + its Postgres + Redis + Sidekiq) | Receives customer messages from channels and delivers replies | Mature open-source support platform with a REST API and signed webhooks | NEXUS Backend (webhooks out, REST in) |

## 3. Diagram

```
                ┌──────────────────────── host (your computer) ───────────────────┐
  Agent ──────► │ NEXUS Frontend (Vite dev server :5173)                          │
  (browser)     │   React + TS + Tailwind   ── /api proxy ──┐                     │
                └───────────────────────────────────────────┼─────────────────────┘
                                                            ▼
┌──────────────────────── docker compose network (nexus_default) ─────────────────┐
│                                                                                 │
│  nexus-backend (FastAPI :8000) ◄──── signed webhook POST ────┐                  │
│   ├─ api/        (NEXUS REST contracts)                      │                  │
│   ├─ services/   (inbox, webhook ingestion, dedupe)          │                  │
│   └─ integrations/chatwoot/  (client, signature, mapper) ───►│ REST + API token │
│        │                                                     │                  │
│        ▼ SQLAlchemy                                          │                  │
│  nexus-db (Postgres 17, host :5433)            chatwoot-rails (:3000) ◄─ Customer│
│   (NEXUS data ONLY)                            chatwoot-sidekiq (sends webhooks)│
│                                                chatwoot-db  (no host port)      │
│                                                chatwoot-redis (no host port)    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Boundaries enforced by this layout:

- The frontend calls **only** the NEXUS Backend. It never knows Chatwoot exists.
- Only `integrations/chatwoot/` understands Chatwoot payloads. Everything else uses NEXUS models.
- Chatwoot's database and Redis have **no host ports**, so nothing outside Chatwoot can read its database.
- Chatwoot API credentials and the webhook secret live only in the backend's environment.

## 4. End-to-end flow in detail

1. **Customer → Chatwoot.** A customer message arrives in a Chatwoot *API channel* inbox
   (for a reproducible demo, `scripts/send-customer-message.sh` uses Chatwoot's public client API).
2. **Chatwoot → Backend.** Chatwoot's Sidekiq worker POSTs a `message_created` event to
   `http://nexus-backend:8000/webhooks/chatwoot`.
3. **Backend validates and stores.**
   - Verifies `X-Chatwoot-Signature` = `sha256=HMAC_SHA256(secret, "<X-Chatwoot-Timestamp>.<raw body>")`.
   - Rejects timestamps older than 5 minutes (replay protection).
   - Inserts into `webhook_events` keyed by `X-Chatwoot-Delivery` (a UUID) — a repeat delivery is a no-op.
   - Maps the payload into NEXUS `conversations` / `messages` (upsert by Chatwoot ID).
4. **Backend → Inbox.** The Inbox polls `GET /api/conversations` every 3 seconds and shows the new message.
   (Real-time push is a later lesson.)
5. **Agent reply → Backend → Chatwoot.** `POST /api/conversations/{id}/messages` → the backend calls
   Chatwoot's create-message API and stores the reply with Chatwoot's returned message ID.
6. **Echo handling.** Chatwoot also sends a `message_created` webhook for that reply. Because the message
   is already stored under the same Chatwoot ID, the upsert updates it instead of duplicating it.

## 5. Folder structure

```
nexus/
├── README.md
├── .env.example            # every variable, no secrets; .env is gitignored
├── .gitignore
├── docker-compose.yml      # all services, pinned image versions
├── backend/
│   ├── Dockerfile  pyproject.toml  alembic.ini  alembic/versions/
│   ├── app/
│   │   ├── main.py  config.py  db.py
│   │   ├── api/            health.py  conversations.py  webhooks.py  dashboard.py
│   │   ├── models/         webhook_event.py  conversation.py  message.py
│   │   ├── schemas/        # NEXUS API shapes (what the frontend sees)
│   │   ├── services/       inbox_service.py  webhook_service.py
│   │   └── integrations/chatwoot/
│   │       client.py  signature.py  mapper.py  payloads.py
│   └── tests/              # signature, dedupe, mapper, API error tests
├── frontend/
│   ├── package.json  vite.config.ts  index.html
│   └── src/
│       ├── app/            router, providers
│       ├── components/layout/   AppShell, Sidebar
│       ├── pages/          Dashboard, Inbox, ComingSoon (Contacts, Automations, Reports, Settings)
│       ├── features/inbox/ ConversationList, MessageThread, ReplyBox
│       ├── lib/api.ts      # the single place that calls the backend
│       └── types/          # mirrors backend/app/schemas
├── scripts/                send-customer-message.sh  replay-webhook.sh
└── docs/
    ├── architecture.md     # this file
    └── lessons/lesson-01.md
```

## 6. API contracts (NEXUS Backend)

| Method | Path | Purpose | Response |
|---|---|---|---|
| GET | `/health/live` | Process is up | `{"status":"ok"}` |
| GET | `/health/ready` | Dependencies are healthy | `{"status", "checks":{"database":"ok", "chatwoot":"ok" \| "not_configured" \| "unreachable"}}` |
| GET | `/api/conversations?status=open` | Inbox list | `[{id, channel, contact:{name,email}, status, last_message_preview, last_activity_at}]` |
| GET | `/api/conversations/{id}` | Conversation header | as above + `external_ref` |
| GET | `/api/conversations/{id}/messages` | Thread | `[{id, direction:"inbound"\|"outbound", author_name, body, created_at, delivery_status}]` |
| POST | `/api/conversations/{id}/messages` | Agent reply | request `{"body": "..."}` → created message |
| POST | `/api/conversations/sync` | Backfill/recover via Chatwoot REST API | `{"imported", "updated"}` |
| POST | `/webhooks/chatwoot` | Chatwoot only (not the UI) | `200 {"result":"accepted"\|"duplicate"}`, `401` invalid signature, `503` secret not configured |
| GET | `/api/dashboard/summary` | Dashboard cards | `{open_conversations, events_today, last_event_at, integration_status}` |

**Error envelope (all endpoints):** `{"error": {"code": "...", "message": "..."}}`

| Code | HTTP | When |
|---|---|---|
| `CHATWOOT_NOT_CONFIGURED` | 503 | API URL / token / account ID missing |
| `CHATWOOT_UNAVAILABLE` | 502 | Chatwoot timed out or returned 5xx |
| `CHATWOOT_AUTH_FAILED` | 502 | Chatwoot rejected the API token (401/403) |
| `CHATWOOT_NOT_FOUND` | 502 | Chatwoot has no such conversation (404) |
| `CHATWOOT_REJECTED` | 502 | Chatwoot refused the request (other 4xx) |
| `WEBHOOK_NOT_CONFIGURED` | 503 | `CHATWOOT_WEBHOOK_SECRET` not set — all webhooks refused (fail closed) |
| `DATABASE_UNAVAILABLE` | 503 | The NEXUS database is not reachable (added in Milestone 3) |
| `INTERNAL_ERROR` | 500 | Anything unexpected — details are logged on the server, never sent to the client |
| `INVALID_SIGNATURE` | 401 | Webhook signature or timestamp check failed |
| `NOT_FOUND` | 404 | Unknown NEXUS conversation ID |
| `VALIDATION_ERROR` | 422 | Bad request body (e.g. empty reply) |

**Failure policy:** the backend starts even with missing credentials and reports `not_configured`;
the webhook endpoint fails closed (rejects everything) until a secret is set; outbound calls use timeouts,
and GET requests retry once.

## 7. Data model (NEXUS DB — separate from Chatwoot's DB)

**`webhook_events`** — audit log and idempotency
`id`, `source`, `delivery_id` **(unique)**, `event_type`, `payload` (JSONB), `signature_valid`,
`status` (`received` / `processed` / `failed`), `error`, `received_at`, `processed_at`

**`conversations`**
`id` (UUID), `source`, `external_account_id`, `external_id`, **unique(`source`, `external_account_id`, `external_id`)**,
`contact_name`, `contact_email`, `status`, `last_message_preview`, `last_activity_at`, `created_at`, `updated_at`

**`messages`**
`id` (UUID), `conversation_id` (FK), `source`, `external_id`, **unique(`source`, `external_id`)**,
`direction`, `author_name`, `body`, `delivery_status`, `created_at`

Duplicate protection has two layers: the delivery UUID stops repeated webhook deliveries, and the unique
Chatwoot message ID stops the same message being stored twice via different paths (webhook vs. reply vs. sync).

## 8. Docker service plan

All image tags were verified to exist on Docker Hub on 2026-11-16.

| Service | Image | Host port | Notes |
|---|---|---|---|
| `nexus-db` | `postgres:17.6-alpine` | `127.0.0.1:5433` | Exposed so students can inspect with `psql` |
| `nexus-backend` | built from `backend/Dockerfile` (`python:3.12-slim`, exact patch pinned in Milestone 3) | `127.0.0.1:8000` | Code bind-mounted, `uvicorn --reload` |
| `chatwoot-rails` | `chatwoot/chatwoot:v4.19.1` | `127.0.0.1:3000` | Web UI + REST API |
| `chatwoot-sidekiq` | `chatwoot/chatwoot:v4.19.1` | — | Background jobs, sends webhooks |
| `chatwoot-db` | `pgvector/pgvector:0.8.1-pg16` | — | Chatwoot's own database |
| `chatwoot-redis` | `redis:7.4.6-alpine` | — | Chatwoot's queue/cache |
| frontend | runs on host via `npm run dev` | `5173` | Vite proxies `/api` → `localhost:8000` |

Ports avoided on purpose: `5000` and `7000` (macOS AirPlay Receiver).

### Required Chatwoot setting for local development

Chatwoot blocks webhooks to private network addresses by default (SSRF protection,
`lib/safe_fetch.rb` in Chatwoot v4.19.1). Because `nexus-backend` is a private Docker address,
Chatwoot needs:

```
SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true   # local development only
```

### One-time Chatwoot setup (students)

1. Open `http://localhost:3000` and complete onboarding (creates account + admin).
2. Profile settings → copy the **access token** → `CHATWOOT_API_TOKEN` in `.env`.
3. Settings → Inboxes → add an **API** channel inbox.
4. Settings → Integrations → Webhooks → add `http://nexus-backend:8000/webhooks/chatwoot`,
   subscribe to `conversation_created`, `conversation_updated`, `conversation_status_changed`,
   `message_created`, `message_updated`, and copy the **secret** → `CHATWOOT_WEBHOOK_SECRET`.

## 9. Library choices

- **Backend:** FastAPI, SQLAlchemy 2 + psycopg 3, Alembic (migrations), httpx (Chatwoot client),
  pydantic-settings (config), pytest.
- **Frontend:** React Router, TanStack Query (fetching + polling), Tailwind CSS. Package manager: npm.

## 10. Environment notes (inspected 2026-11-16)

- macOS 26.6.2 arm64, 16 GB RAM; Docker 29.8.0, Compose v5.5.1; Node 24.16.0, npm 11.13.0.
- Host Python is 3.9.6 (too old) — the backend runs Python 3.12 inside Docker, so students don't need it locally.
- A pre-existing standalone Chatwoot stack (`~/Desktop/chatwoot`) was **stopped, not removed**, and its
  restart policy set to `no`, to free ports 3000/5432/6379. Its volumes are intact.
