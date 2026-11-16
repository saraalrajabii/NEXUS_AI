# Lesson 01 — Foundation + Chatwoot Integration

**Goal:** one working end-to-end flow:

```
Customer message → Chatwoot → NEXUS Backend → NEXUS Inbox → Agent reply → Chatwoot
```

The full design (diagram, API contracts, data model, Docker services) is in
[../architecture.md](../architecture.md). This lesson walks through building it, milestone by milestone.

| Milestone | Status |
|---|---|
| 1. Architecture | ✅ Done |
| 2. Frontend shell, Dashboard, Inbox layout | ✅ Done |
| 3. Backend (FastAPI + PostgreSQL) | ✅ Done |
| 4. Chatwoot integration | ✅ Done |
| 5. End-to-end verification | ✅ Done — all acceptance criteria met ([report](#milestone-5--end-to-end-verification)) |

---

## Prerequisites

| Tool | Version used in this course | Check with |
|---|---|---|
| Docker Desktop (with Compose) | Docker 29.8, Compose v5.5 | `docker --version` and `docker compose version` |
| Node.js | 24.16 (20.19+ works) | `node -v` |
| npm | 11.13 | `npm -v` |
| Git | any recent | `git --version` |

You do **not** need Python installed locally — the backend runs inside Docker.

Ports this lesson uses: **5173** (frontend), **8000** (backend), **3000** (Chatwoot), **5433** (NEXUS database).
Check that they are free before starting:

```bash
lsof -nP -iTCP:5173,8000,3000,5433 -sTCP:LISTEN
```

No output means all ports are free. On macOS, avoid ports 5000 and 7000 — the AirPlay Receiver uses them.

---

## Milestone 2 — The NEXUS frontend

### What problem does it solve?

Agents need one place to work. Instead of sending them into Chatwoot's own interface, NEXUS gives them
an interface we design and control. Later lessons can then plug in more tools (Contacts, Automations…)
behind the same interface.

### Why these technologies?

| Technology | Why |
|---|---|
| **React** | Builds the UI out of small reusable components (a sidebar, a message bubble, a reply box). |
| **TypeScript** | Catches mistakes (a wrong field name, a missing value) before the code ever runs in the browser. |
| **Vite** | Starts in milliseconds and reloads the page the moment you save a file. |
| **Tailwind CSS** | Styles are written next to the markup, from one shared set of design tokens (`src/index.css`). |
| **TanStack Query** | Fetches data from the backend and handles loading, errors, caching and refreshing for us. |
| **React Router** | Gives every page its own URL (`/inbox/abc` opens that conversation directly). |

### How does it talk to the other components?

```
Browser ──► Vite dev server (:5173) ──/api, /health──► NEXUS Backend (:8000)
```

- The browser only ever talks to the Vite dev server.
- Vite **proxies** (forwards) every `/api/...` and `/health/...` request to the backend
  (configured in `frontend/vite.config.ts`).
- All network code lives in **one file**: `src/lib/api.ts`. Nothing in the frontend knows Chatwoot exists,
  and no API keys are stored in the frontend.

### What's in the folder

```
frontend/src/
├── main.tsx                  # entry point: sets up data fetching + routing
├── index.css                 # design tokens (colors, font) for light and dark mode
├── app/router.tsx            # which URL shows which page
├── components/
│   ├── ui.tsx                # small shared pieces: PageHeader, Avatar, StatusDot, ErrorState…
│   └── layout/               # AppShell (the frame), Sidebar, navigation list
├── pages/                    # Dashboard, Inbox, ComingSoon, NotFound
├── features/inbox/           # ConversationList, MessageThread, ReplyBox
├── lib/
│   ├── api.ts                # the ONLY place that calls the backend
│   ├── queries.ts            # data hooks (polling every 3 s for the Inbox)
│   ├── format.ts, status.ts  # small helpers
├── types/api.ts              # NEXUS data shapes (match docs/architecture.md §6)
└── mocks/mockApi.ts          # sample data for VITE_USE_MOCKS=true
```

### Run it

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

All dependency versions are pinned exactly in `package.json`, so everyone gets the same build.

### Two modes

| Mode | How | What you see |
|---|---|---|
| **Real** (default) | `npm run dev` | Talks to the backend. Until Milestone 3, every panel says **"Backend not reachable"** — that is expected. |
| **Sample data** | `VITE_USE_MOCKS=true npm run dev` | Fake conversations, so you can try the layout. The sidebar shows a **"Sample data mode"** badge. Replies are stored in memory only and disappear on reload. |

You can also copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_USE_MOCKS=true` there.

### Verify it works

Run each check and compare with the expected result.

1. **It builds and type-checks.**

   ```bash
   cd frontend
   npm run build
   ```

   Expected: ends with `✓ built in …ms` and no errors.

2. **Lint is clean.**

   ```bash
   npm run lint
   ```

   Expected: no warnings or errors.

3. **The shell loads.** Open <http://localhost:5173>. You see the NEXUS sidebar with Dashboard, Inbox,
   Contacts, Automations, Reports, Settings. The last four are marked **SOON**.

4. **Errors are handled safely.** With no backend running, the Dashboard shows *"Backend not reachable"*
   (code `BACKEND_UNREACHABLE`), all three System health rows say *Unreachable*, and the sidebar
   footer says *Backend offline*. The app does not crash or show a blank page.

   You can see what the proxy returns:

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5173/health/ready
   ```

   Expected: `502` (the proxy cannot reach a backend yet).

5. **The Inbox works with sample data.** Start in sample-data mode, open **Inbox**, click a conversation,
   type a reply and press **Enter**. The reply appears on the right in the accent color, the conversation
   preview on the left updates to *just now*, and the box clears.

6. **Upcoming pages are clearly marked.** Click **Automations**: you see an *Upcoming* badge and a
   "coming soon" explanation, not a broken page.

7. **It works on a phone-sized screen.** Narrow the browser below 768 px: the sidebar turns into a top bar
   of icons, and the Inbox shows the list *or* the open conversation (with a back arrow), never both squeezed.

8. **Dark mode.** Switch your OS to dark mode — the colors follow automatically.

### Results recorded while building this milestone (2026-11-16)

- `npm run build` → `✓ built in 149ms`, no TypeScript errors.
- `npm run lint` (oxlint) → 0 warnings, 0 errors.
- `curl …/health/ready` with no backend → `502`; the UI showed *Backend not reachable* in every panel.
- Sample data mode: sending a reply updated the thread and the conversation list; browser console had no errors.
- At 375 px width the page width equaled the viewport width (no horizontal scroll).

---

## Milestone 3 — The NEXUS backend and database

### What problem does it solve?

The frontend must never hold credentials or talk to Chatwoot. Something has to sit in the middle:
store NEXUS's own data, keep secrets on the server, and translate between Chatwoot and NEXUS.
That is the backend. The database gives it a memory that survives restarts.

### Why these technologies?

| Technology | Why |
|---|---|
| **FastAPI** (Python 3.12) | Small and readable. It validates every request against typed models and generates interactive API docs at `/docs` automatically. |
| **PostgreSQL 17** | Reliable and free. Its **unique constraints** are how we block duplicates: the database itself refuses a second copy. |
| **SQLAlchemy** | Lets us describe tables as Python classes (`app/models/`) and query them safely. |
| **Alembic** | Versioned **migrations**: numbered scripts that create or change tables, so every student's database is identical. |
| **Docker Compose** | One command starts the database and backend, with health checks and the right start-up order. |

### How does it talk to the other components?

```
Frontend ──/api, /health──► nexus-backend (:8000) ──SQL──► nexus-db (Postgres, :5433 on your machine)
                                   │
                                   └── (Milestone 4) Chatwoot REST API
```

- Inside Docker, the backend reaches the database by its **service name**: `nexus-db:5432`.
- From your computer, the database is on `localhost:5433`, and only on `127.0.0.1`, so nothing else on
  your network can reach it.
- Settings come from the root **`.env`** file. `docker-compose.yml` passes the backend only the variables it needs.

### What's in the folder

```
backend/
├── Dockerfile               # python:3.12.13-slim; runs as a non-root user
├── start.sh                 # runs migrations, then starts the API
├── pyproject.toml           # direct dependencies (pinned)
├── requirements.txt         # FULL pinned dependency tree with hashes (generated)
├── alembic.ini, alembic/    # migrations; versions/0001_initial_tables.py creates the tables
├── app/
│   ├── main.py              # creates the FastAPI app, registers routes and error handlers
│   ├── config.py            # settings from environment variables (secrets hidden from logs)
│   ├── db.py                # database connection + "is it up?" check
│   ├── errors.py            # one error format: {"error": {"code", "message"}}
│   ├── models/              # tables: webhook_events, conversations, messages
│   ├── schemas/             # NEXUS API shapes (what the frontend receives)
│   ├── services/            # business logic (inbox queries, dashboard counts)
│   ├── api/                 # routes: health, dashboard, conversations
│   └── integrations/chatwoot/client.py   # Chatwoot reachability (extended in Milestone 4)
└── tests/                   # pytest; uses a separate nexus_test database
infra/nexus-db/init/         # creates the nexus_test database on first start
docker-compose.yml           # nexus-db + nexus-backend
.env.example                 # every setting, no secrets
```

### Run it

```bash
cp .env.example .env
```

Open `.env` and set `NEXUS_DB_PASSWORD`. You can generate one with:

```bash
openssl rand -hex 16
```

Then build and start the services:

```bash
docker compose up -d --build
```

```bash
docker compose ps
```

Expected: both services show `(healthy)` after roughly 20 seconds.

> **macOS:** if `docker compose up` seems to hang the first time, macOS is probably asking whether Docker
> may access the folder the project is in (for example Desktop or Documents). Allow it in the dialog or in
> **System Settings → Privacy & Security → Files & Folders → Docker**. See Troubleshooting.

Useful commands:

| Command | What it does |
|---|---|
| `docker compose logs -f nexus-backend` | Follow the backend logs |
| `docker compose exec nexus-backend pytest -v` | Run the tests inside the container |
| `docker compose exec nexus-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'` | Open a SQL prompt in the NEXUS database |
| `docker compose stop` | Stop the services (data is kept) |
| `docker compose down` | Remove the containers (data is kept in the `nexus_db_data` volume) |

> ⚠️ `docker compose down -v` also deletes the database volume, which means **all NEXUS data**. Only use it when you
> really want to start from zero.

### Design decisions worth noticing

- **Migrations run automatically** at start-up (`start.sh` runs `alembic upgrade head`). The logs show
  `Running upgrade -> 0001` the first time, and nothing afterwards.
- **Duplicates are blocked by the database.** `webhook_events` has `UNIQUE(source, delivery_id)`, and
  `messages` has `UNIQUE(source, external_id)`. Even buggy code can't store the same delivery or message twice.
- **Every error has the same shape.** Each error answers with `{"error": {"code": "...", "message": "..."}}`.
  The frontend uses `code` to choose the explanation it shows.
- **Two kinds of health check:**
  - `/health/live` asks "is the process running?" and never touches the database.
  - `/health/ready` asks "can it do its job?". It returns **503** only when the database is down. With
    Chatwoot missing it still returns 200, but with `status: "degraded"`.
- **Missing Chatwoot credentials are not an error at start-up.** The backend runs and reports
  `chatwoot: not_configured`. Sending a reply returns `CHATWOOT_NOT_CONFIGURED` (503) until Milestone 4.
- **Secrets never appear in logs.** The start-up log lists which settings are present, never their values:
  `chatwoot_api=NOT configured, webhook_secret=NOT set`.
- **Development mode.** The `backend/` folder is mounted into the container and the server reloads on save
  (`NEXUS_RELOAD=true`).

### Verify it works

1. **Services are healthy.**

   ```bash
   docker compose ps
   ```

   Expected: `nexus-db` and `nexus-backend` both show `(healthy)`.

2. **Liveness.**

   ```bash
   curl -s http://localhost:8000/health/live
   ```

   Expected: `{"status":"ok"}`

3. **Readiness.**

   ```bash
   curl -s http://localhost:8000/health/ready
   ```

   Expected: `{"status":"degraded","checks":{"database":"ok","chatwoot":"not_configured"}}`.
   "Degraded" is correct here, because Chatwoot isn't connected yet.

4. **The tables exist.**

   ```bash
   docker compose exec nexus-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
   ```

   Expected: `alembic_version`, `conversations`, `messages`, `webhook_events`.

5. **The API follows the contract.**

   ```bash
   curl -s http://localhost:8000/api/conversations
   ```

   Expected: `[]`

   ```bash
   curl -s "http://localhost:8000/api/conversations?status=banana"
   ```

   Expected: a `VALIDATION_ERROR` envelope (HTTP 422).

6. **Interactive docs.** Open <http://localhost:8000/docs> and try `GET /health/ready` from the browser.

7. **The tests pass.**

   ```bash
   docker compose exec nexus-backend pytest -v
   ```

   Expected: `21 passed`.

8. **The frontend shows live data.** Start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

   Open <http://localhost:5173>. Expected:
   - the Dashboard shows `0` open conversations;
   - backend and database are **Connected** and Chatwoot is **Not configured**;
   - the sidebar footer says *Chatwoot not connected*.

9. **Failure handling: stop the database.**

   ```bash
   docker compose stop nexus-db
   ```

   Then check the backend:

   ```bash
   curl -s -w ' [%{http_code}]\n' http://localhost:8000/health/ready
   ```

   Expected: `database: unreachable` with `[503]`.

   ```bash
   curl -s -w ' [%{http_code}]\n' http://localhost:8000/api/conversations
   ```

   Expected: `DATABASE_UNAVAILABLE` with `[503]`.

   ```bash
   curl -s -w ' [%{http_code}]\n' http://localhost:8000/health/live
   ```

   Expected: `[200]`. The process is still running.

   Now start the database again:

   ```bash
   docker compose start nexus-db
   ```

   Expected: within a few seconds everything works again, without restarting the backend.

### What the tests cover

| File | What it proves |
|---|---|
| `test_health.py` | Liveness; readiness with Chatwoot missing, Chatwoot unreachable, and the database down (503); data endpoints return `DATABASE_UNAVAILABLE` |
| `test_conversations.py` | NEXUS response shape, newest-first ordering, status filter, 404/422 error envelopes, reply without credentials → `CHATWOOT_NOT_CONFIGURED`, empty reply rejected, dashboard counts |
| `test_database_rules.py` | The database rejects duplicate webhook deliveries, duplicate external messages and conversations, and invalid statuses; the models match the migrations (`alembic check`) |

### Results recorded while building this milestone (2026-11-16)

- `docker compose ps` → `nexus-db: Up (healthy)`, `nexus-backend: Up (healthy)`.
- Backend logs: `Running upgrade -> 0001, Initial tables…`, then
  `NEXUS backend starting (database=nexus@nexus-db:5432/nexus, chatwoot_api=NOT configured, webhook_secret=NOT set)`.
- `GET /health/live` → `{"status":"ok"}` [200].
  `GET /health/ready` → `{"status":"degraded","checks":{"database":"ok","chatwoot":"not_configured"}}` [200].
- `GET /api/dashboard/summary` → `{"open_conversations":0,"events_today":0,"last_event_at":null,"integration_status":"not_configured"}` [200].
- `GET /api/conversations?status=banana` → `VALIDATION_ERROR` [422].
  Unknown conversation → `NOT_FOUND` [404]. Unknown route → `NOT_FOUND` [404].
- `\dt` listed `alembic_version, conversations, messages, webhook_events`; the databases `nexus` and `nexus_test` both exist.
- `pytest` → `21 passed, 1 warning in 0.30s`. The warning is a deprecation notice inside Starlette's own test
  client (it recommends a newer httpx package). It does not affect results.
- With `nexus-db` stopped:
  - `/health/ready` → 503 with `database: unreachable`;
  - `/api/conversations` → `DATABASE_UNAVAILABLE` [503];
  - `/health/live` → 200;
  - the sidebar showed *Database unavailable*.

  After `docker compose start nexus-db`, readiness returned to 200 and the API worked again, with no backend restart.
- The frontend Dashboard showed live values: 0 conversations, backend and database *Connected*, Chatwoot *Not configured*.

### Regenerating requirements.txt (maintainers only)

`requirements.txt` is generated from `pyproject.toml` with [uv](https://docs.astral.sh/uv/):

```bash
cd backend
uv pip compile pyproject.toml --extra dev --python-version 3.12 --python-platform linux \
  --generate-hashes --no-header --annotation-style line -o requirements.txt
```

Students don't need to run this.

---

## Milestone 4 — Connecting Chatwoot

### What problem does it solve?

Customers write to us through channels (a website chat, an app, email). Chatwoot already handles those
channels. We keep it running in the background and connect it to NEXUS in two directions:

```
Chatwoot ──webhook (push: "something happened")──► NEXUS backend ──► NEXUS database ──► Inbox
Chatwoot ◄──REST API (pull history, send replies)── NEXUS backend ◄── Agent clicks "send"
```

### Why these mechanisms?

| Mechanism | Why |
|---|---|
| **Webhooks** | Chatwoot tells us immediately when a message arrives. We don't have to ask "anything new?" every few seconds. |
| **HMAC signatures** | The webhook URL could receive requests from anyone. Each request carries a signature that only someone holding the shared secret can produce. We also reject timestamps older than 5 minutes, so a captured request can't be "replayed" later. |
| **Delivery IDs + unique constraints** | Networks retry, and the same event can arrive twice. Each delivery has an `X-Chatwoot-Delivery` id that the database stores only once, and each Chatwoot message id is also stored only once. |
| **REST API (sync)** | Webhooks only report what happens *after* they are set up. Sync pulls existing conversations, and it's also the way to recover if a webhook was ever missed. |
| **REST API (reply)** | Replies go *through* Chatwoot, so Chatwoot delivers them to the customer's channel. |
| **The adapter** (`app/integrations/chatwoot/`) | It is the only code that knows Chatwoot's field names. The rest of NEXUS uses its own models, so the frontend never depends on Chatwoot's format. |

**Not used:** Chatwoot's database. NEXUS never connects to it; its port isn't even exposed.

### How the pieces talk (inside Docker)

| From → To | Address | Why this address |
|---|---|---|
| Chatwoot → NEXUS (webhooks) | `http://nexus-backend:8000/webhooks/chatwoot` | Containers reach each other by **service name** on the Compose network (`nexus_default`) |
| NEXUS → Chatwoot (API) | `http://chatwoot-rails:3000` (`CHATWOOT_BASE_URL`) | Same reason |
| You / scripts → Chatwoot | `http://localhost:3000` | From your computer, use the published port |

> Chatwoot blocks webhooks to **private** addresses by default (protection against server-side request
> forgery). `nexus-backend` is a private Docker address, so `docker-compose.yml` sets
> `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true`. **Local development only.**

### What was added

```
docker-compose.yml           # + chatwoot-db, chatwoot-redis, chatwoot-init, chatwoot-rails, chatwoot-sidekiq
backend/app/integrations/chatwoot/
├── signature.py             # HMAC check (same formula as Chatwoot's lib/webhooks/trigger.rb)
├── mapper.py                # Chatwoot JSON → NEXUS models (handles REST vs webhook differences)
├── client.py                # REST client: timeouts, one retry for GETs, never retries POSTs
└── deps.py                  # how routes get a client (tests swap in a fake)
backend/app/services/
├── store.py                 # idempotent upserts (insert or update by external id)
├── webhook_service.py       # verify → de-duplicate → store → apply
└── chatwoot_service.py      # sync + send reply
backend/app/api/webhooks.py  # POST /webhooks/chatwoot
scripts/
├── chatwoot_setup.py        # creates the API inbox + webhook via Chatwoot's API, writes .env
├── customer.py              # act as a customer (Chatwoot public API): send / show
└── replay_webhook.py        # re-send the last real delivery to prove duplicates are ignored
```

### Set it up

1. **Add the Chatwoot settings to `.env`.** Copy the new lines from `.env.example` and fill in:
   - `CHATWOOT_SECRET_KEY_BASE`: generate with `openssl rand -hex 64`
   - `CHATWOOT_DB_PASSWORD` and `CHATWOOT_REDIS_PASSWORD`: generate each with `openssl rand -hex 16`

   Keep `CHATWOOT_BASE_URL=http://chatwoot-rails:3000`.

2. **Start everything.**

   ```bash
   docker compose up -d
   ```

   The first start pulls the images and prepares Chatwoot's database (the `chatwoot-init` job), so allow
   a few minutes. When it's ready, `docker compose ps` shows every service `healthy`, and `chatwoot-init`
   shows `Exited (0)` because it's a one-off job.

3. **Complete Chatwoot onboarding** at <http://localhost:3000>. Enter a name, company, email and password.
   Test values are fine; this creates the admin account you log in with.

4. **Copy your access token.** In Chatwoot, click your avatar, then **Profile settings → Access Token**.
   Put the token in `.env`:

   ```
   CHATWOOT_API_TOKEN=<your token>
   ```

5. **Connect NEXUS to Chatwoot.**

   ```bash
   python3 scripts/chatwoot_setup.py
   ```

   It checks the token, creates an **API inbox** called "NEXUS API", registers the **webhook** to NEXUS,
   and saves `CHATWOOT_ACCOUNT_ID`, `CHATWOOT_INBOX_IDENTIFIER` and `CHATWOOT_WEBHOOK_SECRET` in `.env`.
   It's safe to run again.

6. **Restart the backend** so it reads the new values.

   ```bash
   docker compose up -d nexus-backend
   ```

> Treat the access token like a password: keep it only in `.env`, never in chat, screenshots or Git.
> If it leaks, reset it in Chatwoot (Profile settings → Access Token) and update `.env`.

### Verify it works

Run each step and compare with the expected result.

1. **The backend can reach Chatwoot.**

   ```bash
   curl -s http://localhost:8000/health/ready
   ```

   Expected: `{"status":"ok","checks":{"database":"ok","chatwoot":"ok"}}`. The Dashboard shows Chatwoot
   **Connected**, and the sidebar says *All systems normal*.

2. **A customer message arrives through the webhook.**

   ```bash
   python3 scripts/customer.py send --new "Hi! My order #4821 still shows as processing."
   ```

   Then look at the backend logs:

   ```bash
   docker compose logs nexus-backend | grep nexus.webhooks
   ```

   Expected: `(conversation_created) → processed` and `(message_created) → processed`. Within 3 seconds the
   conversation appears in the NEXUS Inbox.

3. **A duplicate delivery is ignored.**

   ```bash
   python3 scripts/replay_webhook.py
   ```

   Expected: `result: duplicate`, all row counts the same before and after, and
   `✓ Duplicate ignored — nothing new was stored.`

4. **Forged requests are rejected.** Sending any request to `/webhooks/chatwoot` without a valid signature
   returns **401 `INVALID_SIGNATURE`**, and nothing is stored.

5. **Retrieval with sync.**

   ```bash
   curl -s -X POST http://localhost:8000/api/conversations/sync
   ```

   Run it twice. The second run reports `imported: 0` and creates no duplicates.

6. **A reply from NEXUS reaches Chatwoot.** In the NEXUS Inbox, open the conversation, type a reply and
   press Enter. Then read the conversation from the customer's side:

   ```bash
   python3 scripts/customer.py show
   ```

   Expected: an `[Agent]` line with your reply. You can also see it in Chatwoot's own UI.

7. **The reply isn't stored twice.** Chatwoot sends a `message_created` webhook for your reply too. Count the
   messages:

   ```bash
   docker compose exec nexus-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select external_id, direction, body from messages"'
   ```

   Expected: each message appears **once**.

8. **The tests pass.**

   ```bash
   docker compose exec nexus-backend pytest
   ```

   Expected: `56 passed`.

### What the new tests cover

| File | What it proves |
|---|---|
| `test_signature.py` | Valid signatures pass; wrong secret, tampered body, stale timestamp (replay), missing headers and non-numeric timestamps are rejected |
| `test_mapper.py` | Webhook (text types, ISO time) and REST (numeric types, unix time) both convert correctly; private notes and activity messages are skipped |
| `test_webhooks.py` | Refused without a secret; bad or old signatures rejected and not stored; customer message stored; same delivery twice → `duplicate`; same message via two deliveries → one row; other accounts ignored; status changes applied; malformed payloads stored as `failed` |
| `test_chatwoot_api.py` | Sync imports and is repeatable; GETs retry once; Chatwoot down → `CHATWOOT_UNAVAILABLE`; reply sent and stored; the reply's echo webhook doesn't duplicate it; a failed reply stores nothing and is **not retried**; a rejected token → `CHATWOOT_AUTH_FAILED` and never leaks |

These run against a **fake Chatwoot** (`tests/chatwoot_fixtures.py`), so they're fast and can simulate
outages. The real-service checks are the verification steps above.

### Results recorded while building this milestone (2026-11-16)

- `docker compose ps` → all 7 services healthy, `chatwoot-init: Exited (0)`.
  `GET localhost:3000/api` → `{"version":"4.19.1",…,"queue_services":"ok","data_services":"ok"}`.
- `chatwoot_setup.py` →
  - `✓ Token works … account 1`
  - `✓ Created inbox 'NEXUS API' (id 1)`
  - `✓ Created webhook → http://nexus-backend:8000/webhooks/chatwoot …`
- After the backend restart, the log read `chatwoot_api=configured, webhook_secret=set`, and
  `/health/ready` → `{"status":"ok","checks":{"database":"ok","chatwoot":"ok"}}`.
- `customer.py send --new …` → Chatwoot conversation #1. Within a second NEXUS logged
  `(conversation_created) → processed` and `(message_created) → processed`, both from Chatwoot's Sidekiq
  container. `webhook_events` held 2 rows with `signature_valid = t`.
- `replay_webhook.py` → `{'result': 'duplicate'}`; webhook_events 2→2, messages 1→1, conversations 1→1.
- A request with the wrong secret → 401 `INVALID_SIGNATURE`; a request with no signature → 401; neither was stored.
- Sync, run twice → `{"imported":0,"updated":1,"messages_imported":0}` both times. It recognised the conversation
  the webhook had already stored.
- A reply typed in the NEXUS Inbox → `POST …/messages 201 Created`.
  - `customer.py show` listed `[Agent] Hi Lina! Sorry for the wait…`.
  - Chatwoot's echo `message_created` webhook was processed, and `messages` still held exactly 2 rows
    (Chatwoot ids 1 and 2).
- `pytest` → `56 passed`.

---

## Milestone 5 — End-to-end verification

### What problem does it solve?

Each piece has its own tests, but users only care whether the **whole chain** works. Milestone 5 proves
every transition with real services and real results:

```
Customer message → Chatwoot → NEXUS Backend → NEXUS Inbox → Agent reply → Chatwoot
```

### Run the automated check

With everything running (`docker compose up -d`, plus `npm run dev` in `frontend/`):

```bash
python3 scripts/e2e_check.py
```

It acts as a new customer ("E2E Check"), then checks each step and prints the evidence it saw:

| Check | How it is proven |
|---|---|
| Docker services running | `docker compose ps`: 6 services running (5 report healthy; Sidekiq has no health check), and `chatwoot-init` exited 0 |
| Backend health checks | `/health/live` → 200; `/health/ready` → `{"status":"ok", database ok, chatwoot ok}` |
| Frontend serves NEXUS and reaches backend | `GET localhost:5173` → 200 with `<title>NEXUS</title>`; `/health/ready` through the Vite proxy → 200 |
| 1. Customer → Chatwoot | Chatwoot's **public** API accepts the customer message |
| 2. Chatwoot → NEXUS backend | A signed `message_created` webhook is stored in `webhook_events` with status `processed` |
| 3. NEXUS backend → NEXUS Inbox | `GET /api/conversations` returns the conversation **in NEXUS's own shape**, and its thread contains the message |
| 4. Agent reply → NEXUS backend | `POST /api/conversations/{id}/messages` (the call the Inbox reply box makes) → 201 |
| 5. NEXUS backend → Chatwoot | The customer, reading through Chatwoot's public API, sees the agent reply |
| 6. No duplicate from the echo | Chatwoot's webhook for the reply arrives, and the conversation still has exactly 2 messages in NEXUS |
| 7. Duplicate delivery ignored | `replay_webhook.py` re-sends a real delivery → `duplicate`, and the row counts don't change |

The exit code is `0` only when every check passes, so it can also run in CI later.

### Check it by eye too

1. Open <http://localhost:5173/inbox>. The "E2E Check" conversation shows the customer message on the
   left and the agent reply on the right.
2. Log in to Chatwoot at <http://localhost:3000>. The same conversation shows the same two messages, and the
   reply is attributed to your agent account.

### Acceptance criteria — results (2026-11-16)

| Criterion | Result | Evidence |
|---|---|---|
| Docker services start successfully | ✅ Met | All 7 services healthy, or `Exited (0)` for the init job, on the main stack **and** on a fresh copy |
| Frontend and backend health checks pass | ✅ Met | `/health/live` 200; `/health/ready` `{"status":"ok","checks":{"database":"ok","chatwoot":"ok"}}`; frontend 200 with the NEXUS title; proxy 200; `npm run build` and lint clean |
| The custom NEXUS interface loads | ✅ Met | The Dashboard showed live values; the Inbox showed both conversations with their threads (browser screenshots) |
| A real Chatwoot conversation appears in NEXUS | ✅ Met | Chatwoot conversations #1 and #2, created through Chatwoot's public API, arrived by signed webhook and appeared in the Inbox within seconds |
| A reply sent from NEXUS reaches the Chatwoot conversation | ✅ Met | Replies typed in NEXUS appear as `outgoing` messages #2 and #4 in Chatwoot's **agent** API, and the customer sees them through the **public** API |
| Duplicate webhook delivery does not duplicate stored events | ✅ Met | A replayed real delivery → `duplicate`, with `webhook_events` 8→8, `messages` 4→4, `conversations` 2→2; the reply's echo webhook did not add a second row |
| Setup documentation lets students reproduce the environment | ✅ Met, with one note below | A fresh copy of only the committable files, following these docs, reached a healthy stack, 56/56 tests and Chatwoot onboarding |

`scripts/e2e_check.py` → **10/10 checks passed**, run twice: once before and once after rebuilding every
container. Backend tests: **56 passed**.

### Reproducibility test (how it was done)

1. Copied **only the files Git would commit** into an empty folder (96 files). There was no `.env`, no
   `node_modules`, no build output and no local script state.
2. Followed the README and this lesson exactly:
   - `cp .env.example .env` and generated the secrets with `openssl rand`;
   - `docker compose up -d --build`.
3. Results:
   - all 7 services healthy, and `chatwoot-init` `Exited (0)`;
   - migrations created `alembic_version`, `conversations`, `messages`, `webhook_events`;
   - `/health/ready` → `chatwoot: not_configured` (correct before setup);
   - Chatwoot 4.19.1 redirected to its onboarding page;
   - `pytest` → 56 passed;
   - frontend `npm ci` + `npm run build` + lint passed.
4. Removed the test stack afterwards (only its own containers and volumes).

**Note: what the fresh-copy test did not repeat.** The steps after Chatwoot onboarding (onboarding form →
access token → `chatwoot_setup.py` → `e2e_check.py`) need a person to fill in Chatwoot's sign-up form, so
they were not repeated on the fresh copy. They are the same commands that passed 10/10 on the main stack.
The first real test by a student will cover this.

### Issues found during verification

| Issue | Impact | Resolution |
|---|---|---|
| `npm ci` failed with `EEXIST` on the course machine | Install fails | Caused by a damaged entry in that machine's **global** npm cache, not by the project. The documented fix (`--cache` with a fresh folder, or `npm cache verify`) worked: install, build and lint all passed |
| The compose file pinned the Docker network name to `nexus` | Two copies of the project couldn't run side by side | Removed the fixed name; Compose now uses `<project>_default` (for example `nexus_default`). Services still find each other by name |
| After that change, restarting old containers failed (`network nexus not found`) | One-time error, only for stacks created before the change | `docker compose up -d --force-recreate` (data lives in volumes and is kept) |

### Known limitations (not blockers for Lesson 01)

- **Polling, not push:** the Inbox refreshes every 3 seconds. Real-time updates come in a later lesson.
- **Message history:** sync fetches the most recent 20 messages per conversation (Chatwoot's default page).
  Webhooks capture everything that happens after setup.
- **Not shown:** private notes, activity events ("conversation resolved") and attachments are not shown in NEXUS yet.
- **No retry on webhook failure:** a webhook that fails to apply is stored with status `failed` and its error;
  it can be recovered with `POST /api/conversations/sync`.
- **Local development settings:** `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true` and plain HTTP are for local
  development only. A production deployment needs HTTPS and a public webhook URL.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose up` hangs with containers stuck in `Created` (macOS) | macOS hasn't allowed Docker to read the project folder (Desktop, Documents and Downloads are protected) | Allow the macOS prompt, or turn on **System Settings → Privacy & Security → Files & Folders → Docker → Desktop Folder**, then run `docker compose up -d` again |
| `Set NEXUS_DB_PASSWORD in .env` | `.env` is missing or the password is empty | `cp .env.example .env` and set `NEXUS_DB_PASSWORD` |
| `Bind for 127.0.0.1:5433 failed: port is already allocated` | Another service uses port 5433 | Change `NEXUS_DB_HOST_PORT` in `.env` (the backend is unaffected; it uses port 5432 inside Docker) |
| Backend logs `password authentication failed` | The database volume was created with a different password earlier | Put the original password back in `.env`. Or, if you have no data to keep, delete the volume with `docker compose down -v` (⚠️ deletes all NEXUS data) |
| `nexus_test` database missing when running tests | The init script only runs when the volume is first created | `docker compose exec nexus-db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE nexus_test"'` |
| API answers `DATABASE_UNAVAILABLE` | The database container is stopped or unhealthy | `docker compose ps`, then `docker compose start nexus-db` |
| `network nexus not found` when starting | Containers were created by an older version of `docker-compose.yml` that used a fixed network name | `docker compose up -d --force-recreate` (keeps all data) |
| `localhost:3000` doesn't load for a few minutes after the first `up` | `chatwoot-init` is still preparing Chatwoot's database | Watch it with `docker compose logs -f chatwoot-init`. It should end with `Exited (0)` |
| `Bind for 127.0.0.1:3000 failed` | Another app (or an older Chatwoot) uses port 3000 | Stop that app, or change `CHATWOOT_HOST_PORT` in `.env` |
| `/health/ready` shows `chatwoot: not_configured` | `CHATWOOT_ACCOUNT_ID` or `CHATWOOT_API_TOKEN` is empty, or the backend wasn't restarted | Fill them in, then run `docker compose up -d nexus-backend` |
| `/health/ready` shows `chatwoot: error` | The token is wrong or was reset | Copy it again from Chatwoot's Profile settings, update `.env`, restart the backend |
| `chatwoot: unreachable` | Chatwoot is down, or `CHATWOOT_BASE_URL` uses `localhost` | Use `http://chatwoot-rails:3000`. Inside Docker, `localhost` means the backend container itself |
| Customer messages never reach NEXUS | The webhook isn't registered, Sidekiq is down, or the safe-fetch setting is missing | Run `python3 scripts/chatwoot_setup.py` again, check `docker compose ps chatwoot-sidekiq`, and confirm `SAFE_FETCH_ALLOW_PRIVATE_NETWORK: 'true'` in `docker-compose.yml`. Use `POST /api/conversations/sync` to catch up |
| Backend logs `Rejected webhook: signature does not match` | `CHATWOOT_WEBHOOK_SECRET` in `.env` doesn't match Chatwoot's webhook | Run `python3 scripts/chatwoot_setup.py` again (it rewrites the secret), then restart the backend |
| Webhook answers 503 `WEBHOOK_NOT_CONFIGURED` | No webhook secret is set, so NEXUS refuses all webhooks (safe default) | Same as above |
| Replying shows *Reply not sent: Chatwoot rejected the API token* | `CHATWOOT_AUTH_FAILED`: the token is invalid | Update `CHATWOOT_API_TOKEN` and restart the backend |
| `npm install` fails with `EEXIST` and a path under `~/.npm/_cacache` | A corrupted entry in npm's download cache (not a problem with the project) | Run `npm cache verify`, or install with a fresh cache: `npm install --cache /tmp/npm-cache-nexus` |
| `Port 5173 is already in use` | Another Vite app is running (we use `strictPort` so it fails instead of silently switching ports) | Stop the other app, or find it with `lsof -nP -iTCP:5173 -sTCP:LISTEN` |
| Every panel says *Backend not reachable* | The backend isn't running yet (normal before Milestone 3) | Start the backend, or use sample-data mode |
| Code shows `HTTP_ERROR` | The backend answered, but with an unexpected error | Check the backend logs (Milestone 3) |
| Styles look unstyled / plain HTML | Tailwind plugin not loaded | Confirm `tailwindcss()` is in `plugins` in `vite.config.ts`, then restart `npm run dev` |
| Sample-data reply vanished after refresh | Sample data is kept in memory only | Expected — real replies are stored once the backend exists |
