#!/usr/bin/env python3
"""Simulate Chatwoot delivering the SAME webhook again (a duplicate delivery).

It takes the most recent webhook NEXUS received, re-signs it with the real secret
(so it passes authentication) and sends it again with the SAME X-Chatwoot-Delivery id.
NEXUS should answer "duplicate" and store nothing new.

Usage:  python3 scripts/replay_webhook.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
import time

from _common import ROOT, http, read_env

QUERY = (
    "SELECT json_build_object('delivery_id', delivery_id, 'event_type', event_type, 'payload', payload) "
    "FROM webhook_events ORDER BY id DESC LIMIT 1"
)


def count(table: str) -> int:
    return int(psql(f"SELECT count(*) FROM {table}"))


def psql(sql: str) -> str:
    cmd = ["docker", "compose", "exec", "-T", "nexus-db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "{sql}"']
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    env = read_env()
    secret = env.get("CHATWOOT_WEBHOOK_SECRET")
    if not secret:
        sys.exit("CHATWOOT_WEBHOOK_SECRET is empty in .env. Run: python3 scripts/chatwoot_setup.py")
    row = psql(QUERY)
    if not row:
        sys.exit("NEXUS has not received any webhook yet. Send a customer message first.")
    last = json.loads(row)

    body = json.dumps(last["payload"]).encode()
    ts = str(int(time.time()))
    signature = "sha256=" + hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()

    before = {t: count(t) for t in ("webhook_events", "messages", "conversations")}
    port = env.get("NEXUS_BACKEND_HOST_PORT") or "8000"
    status, answer = http(
        "POST", f"http://localhost:{port}/webhooks/chatwoot", raw=body,
        headers={"X-Chatwoot-Delivery": last["delivery_id"], "X-Chatwoot-Timestamp": ts, "X-Chatwoot-Signature": signature},
    )
    after = {t: count(t) for t in before}

    print(f"Replayed delivery {last['delivery_id']} ({last['event_type']})")
    print(f"NEXUS answered: HTTP {status} {answer}")
    for table in before:
        print(f"  {table:<15} before={before[table]}  after={after[table]}")
    ok = status == 200 and answer.get("result") == "duplicate" and before == after
    print("✓ Duplicate ignored — nothing new was stored." if ok else "✗ Unexpected result!")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
