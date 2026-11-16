#!/usr/bin/env python3
"""Pretend to be a customer, using Chatwoot's PUBLIC client API (what a chat widget or app uses).

    python3 scripts/customer.py send "Hi! Where is my order?"     # message in the current conversation
    python3 scripts/customer.py send --new "A different question"  # start a new conversation
    python3 scripts/customer.py show                               # read the conversation as the customer sees it

The customer's identity is remembered in scripts/.customer.json (gitignored), so follow-up
messages land in the same conversation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from _common import chatwoot_url, http, read_env

STATE = Path(__file__).resolve().parent / ".customer.json"


def public_base(env: dict) -> str:
    inbox = env.get("CHATWOOT_INBOX_IDENTIFIER")
    if not inbox:
        sys.exit("CHATWOOT_INBOX_IDENTIFIER is missing in .env. Run: python3 scripts/chatwoot_setup.py")
    return f"{chatwoot_url(env)}/public/api/v1/inboxes/{inbox}"


def ensure_conversation(base: str, new: bool, name: str) -> dict:
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if new or "contact" not in state:
        stamp = int(time.time())
        status, contact = http("POST", f"{base}/contacts", body={"name": name, "email": f"customer{stamp}@example.test"})
        if status != 200:
            sys.exit(f"Could not create contact (HTTP {status}): {contact}")
        state = {"contact": contact["source_id"], "name": contact.get("name")}
    if new or "conversation" not in state:
        status, conv = http("POST", f"{base}/contacts/{state['contact']}/conversations", body={})
        if status != 200:
            sys.exit(f"Could not create conversation (HTTP {status}): {conv}")
        state["conversation"] = conv["id"]
        print(f"Started Chatwoot conversation #{conv['id']} as {state['name']!r}")
    STATE.write_text(json.dumps(state, indent=2))
    return state


def send(args, env) -> None:
    base = public_base(env)
    state = ensure_conversation(base, args.new, args.name)
    url = f"{base}/contacts/{state['contact']}/conversations/{state['conversation']}/messages"
    status, msg = http("POST", url, body={"content": args.text})
    if status != 200:
        sys.exit(f"Could not send (HTTP {status}): {msg}")
    print(f"✓ Customer sent message #{msg['id']} in conversation #{state['conversation']}: {args.text!r}")


def show(_args, env) -> None:
    if not STATE.exists():
        sys.exit("No customer conversation yet. Send one first: python3 scripts/customer.py send \"Hello\"")
    state = json.loads(STATE.read_text())
    base = public_base(env)
    url = f"{base}/contacts/{state['contact']}/conversations/{state['conversation']}/messages"
    status, messages = http("GET", url)
    if status != 200:
        sys.exit(f"Could not read messages (HTTP {status}): {messages}")
    print(f"Conversation #{state['conversation']} as seen by the customer:")
    for m in messages:
        who = "Customer" if m.get("message_type") == 0 else "Agent   "
        print(f"  [{who}] {m.get('content')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_send = sub.add_parser("send", help="send a customer message")
    p_send.add_argument("text")
    p_send.add_argument("--new", action="store_true", help="start a new conversation (new customer)")
    p_send.add_argument("--name", default="Lina Haddad", help="customer name for a new conversation")
    sub.add_parser("show", help="show the conversation from the customer's side")
    args = parser.parse_args()
    {"send": send, "show": show}[args.cmd](args, read_env())


if __name__ == "__main__":
    main()
