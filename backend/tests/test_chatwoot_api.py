"""Retrieval (sync) and replies through Chatwoot's API, including failures."""

import httpx
from sqlalchemy import func, select

from app.models import Message
from tests.chatwoot_fixtures import rest_conversation, rest_message, signed_headers, to_body, webhook_message


def message_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Message))


def seed(fake):
    fake.conversations = [rest_conversation(1), rest_conversation(2, status="resolved")]
    fake.messages = {
        "1": [rest_message(11, "Hi there"), rest_message(12, "Note", message_type=1, private=True)],
        "2": [rest_message(21, "Thanks, solved")],
    }


# ── sync ──────────────────────────────────────────────────────────────────────
def test_sync_imports_conversations_and_messages(connected_client, fake_chatwoot, db):
    seed(fake_chatwoot)
    r = connected_client.post("/api/conversations/sync")
    assert r.status_code == 200
    assert r.json() == {"imported": 2, "updated": 0, "messages_imported": 2}  # private note skipped
    assert {c["status"] for c in connected_client.get("/api/conversations").json()} == {"open", "resolved"}


def test_sync_twice_creates_no_duplicates(connected_client, fake_chatwoot, db):
    seed(fake_chatwoot)
    connected_client.post("/api/conversations/sync")
    r = connected_client.post("/api/conversations/sync")
    assert r.json() == {"imported": 0, "updated": 2, "messages_imported": 0}
    assert message_count(db) == 2


def test_sync_without_credentials(client):
    r = client.post("/api/conversations/sync")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CHATWOOT_NOT_CONFIGURED"


def test_get_requests_retry_once_then_succeed(connected_client, fake_chatwoot):
    seed(fake_chatwoot)
    fake_chatwoot.fail_with, fake_chatwoot.fail_times = 503, 1
    assert connected_client.post("/api/conversations/sync").status_code == 200


def test_chatwoot_down_during_sync(connected_client, fake_chatwoot):
    fake_chatwoot.fail_with = httpx.ConnectTimeout("timed out")
    r = connected_client.post("/api/conversations/sync")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "CHATWOOT_UNAVAILABLE"


# ── replies ───────────────────────────────────────────────────────────────────
def _synced_conversation_id(client, fake):
    seed(fake)
    client.post("/api/conversations/sync")
    return next(c["id"] for c in client.get("/api/conversations").json() if c["status"] == "open")


def test_reply_is_sent_to_chatwoot_and_stored(connected_client, fake_chatwoot, db):
    conv_id = _synced_conversation_id(connected_client, fake_chatwoot)
    r = connected_client.post(f"/api/conversations/{conv_id}/messages", json={"body": "  On it!  "})
    assert r.status_code == 201
    assert (r.json()["body"], r.json()["direction"]) == ("On it!", "outbound")
    assert ("POST", "/api/v1/accounts/1/conversations/1/messages") in fake_chatwoot.calls
    assert fake_chatwoot.messages["1"][-1]["content"] == "On it!"  # reached "Chatwoot"


def test_reply_echo_webhook_does_not_duplicate(connected_client, fake_chatwoot, db):
    conv_id = _synced_conversation_id(connected_client, fake_chatwoot)
    sent = connected_client.post(f"/api/conversations/{conv_id}/messages", json={"body": "On it!"}).json()
    before = message_count(db)

    # Chatwoot now sends message_created for the reply we just sent (same Chatwoot message id).
    chatwoot_id = fake_chatwoot.messages["1"][-1]["id"]
    echo = webhook_message(msg_id=chatwoot_id, content="On it!", message_type="outgoing", conv_id=1)
    body = to_body(echo)
    connected_client.post("/webhooks/chatwoot", content=body, headers=signed_headers(body, "echo-1"))

    assert message_count(db) == before
    thread = connected_client.get(f"/api/conversations/{conv_id}/messages").json()
    assert [m["id"] for m in thread].count(sent["id"]) == 1


def test_reply_when_chatwoot_fails_stores_nothing_and_is_not_retried(connected_client, fake_chatwoot, db):
    conv_id = _synced_conversation_id(connected_client, fake_chatwoot)
    before = message_count(db)
    fake_chatwoot.calls.clear()
    fake_chatwoot.fail_with = 500

    r = connected_client.post(f"/api/conversations/{conv_id}/messages", json={"body": "Hello?"})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "CHATWOOT_UNAVAILABLE"
    assert message_count(db) == before
    assert [c for c in fake_chatwoot.calls if c[0] == "POST"] == [("POST", "/api/v1/accounts/1/conversations/1/messages")]


def test_reply_with_rejected_token(connected_client, fake_chatwoot, db):
    conv_id = _synced_conversation_id(connected_client, fake_chatwoot)
    fake_chatwoot.fail_with = 401
    r = connected_client.post(f"/api/conversations/{conv_id}/messages", json={"body": "Hello?"})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "CHATWOOT_AUTH_FAILED"
    assert "test-token" not in r.text  # the token never leaks into responses


def test_readiness_ok_when_chatwoot_answers(connected_client, fake_chatwoot, monkeypatch):
    import app.api.health as health

    monkeypatch.setattr(health, "chatwoot_status", lambda s: _status_with_fake(s, fake_chatwoot))
    r = connected_client.get("/health/ready")
    assert r.json() == {"status": "ok", "checks": {"database": "ok", "chatwoot": "ok"}}


def _status_with_fake(settings, fake):
    from app.integrations.chatwoot.client import chatwoot_status

    return chatwoot_status(settings, transport=fake.transport)
