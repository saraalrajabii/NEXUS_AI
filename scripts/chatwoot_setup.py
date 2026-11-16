#!/usr/bin/env python3
"""Connect NEXUS to Chatwoot using Chatwoot's official REST API (never its database).

Before running: complete Chatwoot onboarding at http://localhost:3000 and put your
access token (Profile settings → Access Token) in .env as CHATWOOT_API_TOKEN.

What it does (safe to run again — it reuses what already exists):
  1. Checks the token works (GET /api/v1/profile) and finds your account id.
  2. Creates an "API" channel inbox called "NEXUS API" (customers' messages arrive here).
  3. Registers a webhook pointing at the NEXUS backend and saves its secret in .env.

Usage:  python3 scripts/chatwoot_setup.py
"""

from __future__ import annotations

import sys

from _common import chatwoot_url, http, read_env, write_env

INBOX_NAME = "NEXUS API"
WEBHOOK_URL = "http://nexus-backend:8000/webhooks/chatwoot"  # Chatwoot reaches NEXUS inside Docker
WEBHOOK_EVENTS = [
    "conversation_created",
    "conversation_updated",
    "conversation_status_changed",
    "message_created",
    "message_updated",
]


def main() -> None:
    env = read_env()
    base = chatwoot_url(env)
    token = env.get("CHATWOOT_API_TOKEN", "")
    if not token:
        sys.exit("CHATWOOT_API_TOKEN is empty in .env. Copy it from Chatwoot → Profile settings → Access Token.")
    auth = {"api_access_token": token}

    # 1. Token + account
    status, profile = http("GET", f"{base}/api/v1/profile", headers=auth)
    if status != 200:
        sys.exit(f"Chatwoot rejected the token (HTTP {status}). Check CHATWOOT_API_TOKEN in .env.")
    account_id = env.get("CHATWOOT_ACCOUNT_ID") or str(profile["accounts"][0]["id"])
    write_env("CHATWOOT_ACCOUNT_ID", account_id)
    print(f"✓ Token works — signed in as {profile.get('name')!r}, account {account_id}")
    api = f"{base}/api/v1/accounts/{account_id}"

    # 2. API inbox
    status, inboxes = http("GET", f"{api}/inboxes", headers=auth)
    inbox = next((i for i in inboxes.get("payload", []) if i.get("name") == INBOX_NAME), None)
    if inbox:
        print(f"✓ Inbox {INBOX_NAME!r} already exists (id {inbox['id']})")
    else:
        status, inbox = http(
            "POST", f"{api}/inboxes", headers=auth, body={"name": INBOX_NAME, "channel": {"type": "api", "webhook_url": ""}}
        )
        if status != 200:
            sys.exit(f"Could not create the inbox (HTTP {status}): {inbox}")
        print(f"✓ Created inbox {INBOX_NAME!r} (id {inbox['id']})")
    write_env("CHATWOOT_INBOX_IDENTIFIER", inbox["inbox_identifier"])

    # 3. Webhook → NEXUS
    status, hooks = http("GET", f"{api}/webhooks", headers=auth)
    hook = next((h for h in hooks["payload"]["webhooks"] if h.get("url") == WEBHOOK_URL), None)
    if hook:
        print(f"✓ Webhook to {WEBHOOK_URL} already exists (id {hook['id']})")
    else:
        status, created = http(
            "POST", f"{api}/webhooks", headers=auth,
            body={"webhook": {"name": "NEXUS", "url": WEBHOOK_URL, "subscriptions": WEBHOOK_EVENTS}},
        )
        if status != 200:
            sys.exit(f"Could not create the webhook (HTTP {status}): {created}")
        hook = created["payload"]["webhook"]
        print(f"✓ Created webhook → {WEBHOOK_URL} for {', '.join(WEBHOOK_EVENTS)}")
    write_env("CHATWOOT_WEBHOOK_SECRET", hook["secret"])

    print("\nSaved CHATWOOT_ACCOUNT_ID, CHATWOOT_INBOX_IDENTIFIER and CHATWOOT_WEBHOOK_SECRET in .env.")
    print("Now restart the backend so it picks them up:\n\n    docker compose up -d nexus-backend\n")


if __name__ == "__main__":
    main()
