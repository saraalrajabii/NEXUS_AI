#!/usr/bin/env python3
"""End-to-end check for Lesson 01. Verifies every transition with real services:

    Customer message → Chatwoot → NEXUS Backend → NEXUS Inbox → Agent reply → Chatwoot

Each step prints PASS/FAIL with the evidence it saw. Exit code 0 only if every step passed.
It creates one new test conversation each run (as customer "E2E Check").

Usage:  python3 scripts/e2e_check.py
Needs:  docker compose up -d   +   frontend dev server (cd frontend && npm run dev)
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request

from _common import ROOT, chatwoot_url, http, read_env

results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, evidence: str) -> bool:
    results.append((name, ok, evidence))
    print(f"{'PASS' if ok else 'FAIL'}  {name}\n      {evidence}")
    return ok


def wait_for(fn, timeout: float = 20, interval: float = 1):
    """Call fn() until it returns something truthy (or time runs out)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(interval)
    return None


def psql(sql: str) -> str:
    cmd = ["docker", "compose", "exec", "-T", "nexus-db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "{sql}"']
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    env = read_env()
    backend = f"http://localhost:{env.get('NEXUS_BACKEND_HOST_PORT') or '8000'}"
    frontend = "http://localhost:5173"
    cw = chatwoot_url(env)
    inbox = env.get("CHATWOOT_INBOX_IDENTIFIER")
    if not inbox:
        sys.exit("CHATWOOT_INBOX_IDENTIFIER missing — run scripts/chatwoot_setup.py first.")
    public = f"{cw}/public/api/v1/inboxes/{inbox}"
    marker = f"E2E-{int(time.time())}"

    print(f"\n== Lesson 01 end-to-end check ({marker}) ==\n")

    # 0. Services and health checks
    lines = subprocess.run(["docker", "compose", "ps", "-a", "--format", "{{.Service}}\t{{.Status}}"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
    services = dict(line.split("\t", 1) for line in lines)

    def service_ok(name: str, state: str) -> bool:
        if name == "chatwoot-init":  # one-off job: must have finished successfully
            return state.startswith("Exited (0)")
        if name == "chatwoot-sidekiq":  # no healthcheck defined: running is enough
            return state.startswith("Up")
        return "(healthy)" in state

    problems = {n: s for n, s in services.items() if not service_ok(n, s)}
    step("Docker services running", len(services) == 7 and not problems,
         f"{len(services)} services; problems: {problems or 'none'}")

    status, live = http("GET", f"{backend}/health/live")
    status_r, ready = http("GET", f"{backend}/health/ready")
    step("Backend health checks", status == 200 and status_r == 200 and ready.get("status") == "ok",
         f"/health/live → {status} {live}; /health/ready → {status_r} {ready}")

    try:
        with urllib.request.urlopen(frontend, timeout=5) as r:
            html = r.read().decode()
        fe_ok = r.status == 200 and "<title>NEXUS</title>" in html
        status_p, via_proxy = http("GET", f"{frontend}/health/ready")
        step("Frontend serves NEXUS and reaches backend", fe_ok and status_p == 200,
             f"GET / → {r.status}, title NEXUS={'yes' if fe_ok else 'no'}; /health/ready via proxy → {status_p}")
    except OSError as exc:
        step("Frontend serves NEXUS and reaches backend", False, f"{frontend} not reachable ({exc}). Run: cd frontend && npm run dev")

    # 1. Customer → Chatwoot
    _, contact = http("POST", f"{public}/contacts", body={"name": "E2E Check", "email": f"{marker.lower()}@example.test"})
    _, conv = http("POST", f"{public}/contacts/{contact['source_id']}/conversations", body={})
    text = f"Hello from the customer ({marker})"
    status, msg = http("POST", f"{public}/contacts/{contact['source_id']}/conversations/{conv['id']}/messages",
                       body={"content": text})
    step("1. Customer message → Chatwoot", status == 200, f"Chatwoot conversation #{conv['id']}, message #{msg.get('id')}")
    cw_conv = str(conv["id"])

    # 2. Chatwoot → NEXUS backend (webhook)
    def nexus_conversation():
        _, items = http("GET", f"{backend}/api/conversations")
        return next((c for c in items if c.get("last_message_preview") == text), None)

    found = wait_for(nexus_conversation)
    events = psql(
        "SELECT string_agg(event_type || ':' || status, ', ') FROM webhook_events "
        f"WHERE payload->'conversation'->>'id' = '{cw_conv}' OR (payload->>'id' = '{cw_conv}' AND event_type LIKE 'conversation%')"
    )
    step("2. Chatwoot → NEXUS backend (signed webhook stored)", bool(found) and "message_created:processed" in events,
         f"webhook_events for conversation #{cw_conv}: {events or 'none'}")
    if not found:
        return finish()

    # 3. NEXUS backend → NEXUS Inbox (the API the Inbox uses, in NEXUS's shape)
    _, thread = http("GET", f"{backend}/api/conversations/{found['id']}/messages")
    nexus_shape = set(found) == {"id", "channel", "contact", "status", "last_message_preview", "last_activity_at"}
    step("3. NEXUS backend → NEXUS Inbox API (NEXUS models, not Chatwoot's)",
         nexus_shape and [m["body"] for m in thread] == [text],
         f"conversation {found['id']} contact={found['contact']['name']!r}; thread={[m['body'] for m in thread]}")

    # 4. Agent reply → NEXUS → Chatwoot
    reply = f"Agent reply from NEXUS ({marker})"
    status, sent = http("POST", f"{backend}/api/conversations/{found['id']}/messages", body={"body": reply})
    step("4. Agent reply → NEXUS backend", status == 201, f"POST …/messages → {status}, NEXUS message {sent.get('id')}")

    def customer_sees_reply():
        _, msgs = http("GET", f"{public}/contacts/{contact['source_id']}/conversations/{cw_conv}/messages")
        return [m["content"] for m in msgs if m.get("message_type") == 1 and m.get("content") == reply]

    seen = wait_for(customer_sees_reply, timeout=10)
    step("5. NEXUS backend → Chatwoot (customer can see the reply)", bool(seen),
         f"Chatwoot public API for conversation #{cw_conv}: agent messages = {seen}")

    # 6. Echo webhook for the reply must not duplicate it
    def echo_processed():
        n = psql(
            "SELECT count(*) FROM webhook_events WHERE event_type = 'message_created' "
            f"AND payload->'conversation'->>'id' = '{cw_conv}' AND payload->>'message_type' = 'outgoing'"
        )
        return int(n) >= 1

    echoed = wait_for(echo_processed, timeout=15)
    count = psql(f"SELECT count(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.external_id = '{cw_conv}'")
    step("6. Reply's echo webhook does not duplicate it", bool(echoed) and count == "2",
         f"echo webhook received={bool(echoed)}; NEXUS messages in this conversation = {count} (expected 2)")

    # 7. Duplicate delivery of a real webhook
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "replay_webhook.py")], cwd=ROOT, capture_output=True, text=True)
    last_lines = " | ".join(line.strip() for line in proc.stdout.splitlines()[1:5])
    step("7. Duplicate webhook delivery is ignored", proc.returncode == 0, last_lines)

    finish()


def finish() -> None:
    passed = sum(ok for _, ok, _ in results)
    print(f"\n== {passed}/{len(results)} checks passed ==")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
