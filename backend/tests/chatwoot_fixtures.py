"""A fake Chatwoot for tests, plus realistic payloads.

Payload shapes follow Chatwoot v4.19.1 (Message#webhook_data, Conversations::EventDataPresenter,
api/v1/models/_message.json.jbuilder).
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.chatwoot.signature import compute_signature

ACCOUNT_ID = "1"
SECRET = "test-webhook-secret"
NOW = int(time.time())
ISO_NOW = datetime.fromtimestamp(NOW, tz=UTC).isoformat().replace("+00:00", ".000Z")  # same format Chatwoot uses


def webhook_conversation(conv_id: int = 7, status: str = "open", account_id: int = 1) -> dict[str, Any]:
    return {
        "id": conv_id,
        "status": status,
        "channel": "Channel::Api",
        "inbox_id": 1,
        "meta": {"sender": {"id": 3, "name": "Lina Haddad", "email": "lina@example.test", "type": "contact"}},
        "messages": [],
        "last_activity_at": NOW,
        "timestamp": NOW,
        "created_at": NOW - 60,
        "account": {"id": account_id, "name": "NEXUS Demo"},
    }


def webhook_message(
    msg_id: int = 101,
    content: str = "Hi, where is my order?",
    message_type: str = "incoming",
    conv_id: int = 7,
    account_id: int = 1,
    private: bool = False,
) -> dict[str, Any]:
    return {
        "event": "message_created",
        "id": msg_id,
        "content": content,
        "message_type": message_type,  # webhooks send TEXT
        "content_type": "text",
        "private": private,
        "created_at": ISO_NOW,  # webhooks send ISO text
        "sender": {"id": 3, "name": "Lina Haddad", "type": "contact"},
        "conversation": webhook_conversation(conv_id, account_id=account_id),
        "account": {"id": account_id, "name": "NEXUS Demo"},
        "inbox": {"id": 1, "name": "NEXUS API"},
    }


def signed_headers(body: bytes, delivery_id: str = "delivery-1", secret: str = SECRET, ts: int | None = None) -> dict[str, str]:
    timestamp = str(ts if ts is not None else int(time.time()))
    return {
        "Content-Type": "application/json",
        "X-Chatwoot-Delivery": delivery_id,
        "X-Chatwoot-Timestamp": timestamp,
        "X-Chatwoot-Signature": compute_signature(secret, timestamp, body),
    }


def to_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode()


def rest_conversation(conv_id: int, status: str = "open", last: str | None = "Hello") -> dict[str, Any]:
    return {
        "id": conv_id,
        "status": status,
        "account_id": 1,
        "inbox_id": 1,
        "meta": {"sender": {"id": conv_id, "name": f"Customer {conv_id}", "email": None}, "channel": "Channel::Api"},
        "messages": [],
        "last_non_activity_message": {"id": conv_id * 100, "content": last} if last else None,
        "last_activity_at": NOW - conv_id,
        "timestamp": NOW - conv_id,
    }


def rest_message(msg_id: int, content: str, message_type: int = 0, private: bool = False) -> dict[str, Any]:
    return {
        "id": msg_id,
        "content": content,
        "message_type": message_type,  # REST sends a NUMBER
        "status": "sent",
        "created_at": NOW - 1000 + msg_id,  # REST sends unix seconds
        "private": private,
        "sender": {"id": 9, "name": "Agent Smith" if message_type == 1 else "Customer", "type": "user"},
    }


@dataclass
class FakeChatwoot:
    """Answers like Chatwoot's REST API. Set `fail_with` to simulate outages."""

    conversations: list[dict[str, Any]] = field(default_factory=list)
    messages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    fail_with: int | Exception | None = None  # e.g. 500, 401, or httpx.ConnectTimeout(...)
    fail_times: int = 1_000_000  # how many requests fail before recovering
    calls: list[tuple[str, str]] = field(default_factory=list)
    next_message_id: int = 9000

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        if self.fail_with is not None and self.fail_times > 0:
            self.fail_times -= 1
            if isinstance(self.fail_with, Exception):
                raise self.fail_with
            return httpx.Response(self.fail_with, json={"error": "boom"})

        assert request.headers.get("api_access_token") == "test-token", "token header missing"
        path = request.url.path
        if path == "/api/v1/profile":
            return httpx.Response(200, json={"id": 9, "name": "Agent Smith"})
        if path == f"/api/v1/accounts/{ACCOUNT_ID}/conversations" and request.method == "GET":
            page = int(request.url.params.get("page", "1"))
            batch = self.conversations[(page - 1) * 25 : page * 25]
            return httpx.Response(200, json={"data": {"meta": {}, "payload": batch}})
        if path.endswith("/messages"):
            conv_id = path.split("/")[-2]
            if request.method == "GET":
                return httpx.Response(200, json={"meta": {}, "payload": self.messages.get(conv_id, [])})
            body = json.loads(request.content)
            self.next_message_id += 1
            created = {**rest_message(self.next_message_id, body["content"], message_type=1), "conversation_id": int(conv_id)}
            self.messages.setdefault(conv_id, []).append(created)
            return httpx.Response(200, json=created)
        return httpx.Response(404, json={"error": "not found"})

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)
