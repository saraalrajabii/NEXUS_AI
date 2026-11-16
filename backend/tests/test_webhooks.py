"""The webhook receiver: authentication, de-duplication, storage."""

import time

from sqlalchemy import func, select

from app.models import Conversation, Message, WebhookEvent
from tests.chatwoot_fixtures import signed_headers, to_body, webhook_conversation, webhook_message

URL = "/webhooks/chatwoot"


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def post(client, payload, delivery_id="delivery-1", **kw):
    body = to_body(payload)
    return client.post(URL, content=body, headers=signed_headers(body, delivery_id, **kw))


def test_refused_when_secret_not_configured(client, db):
    r = post(client, webhook_message())
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "WEBHOOK_NOT_CONFIGURED"
    assert count(db, WebhookEvent) == 0


def test_bad_signature_is_rejected_and_not_stored(connected_client, db):
    r = post(connected_client, webhook_message(), secret="not-the-secret")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_SIGNATURE"
    assert count(db, WebhookEvent) == 0


def test_replayed_old_request_is_rejected(connected_client, db):
    r = post(connected_client, webhook_message(), ts=int(time.time()) - 3600)
    assert r.status_code == 401


def test_customer_message_creates_conversation_and_message(connected_client, db):
    r = post(connected_client, webhook_message(content="Where is order #4821?"))
    assert r.status_code == 200
    assert r.json() == {"result": "accepted", "delivery_id": "delivery-1"}

    conv = db.scalar(select(Conversation))
    msg = db.scalar(select(Message))
    assert (conv.external_id, conv.contact_name, conv.status) == ("7", "Lina Haddad", "open")
    assert (msg.body, msg.direction, msg.external_id) == ("Where is order #4821?", "inbound", "101")
    assert conv.last_message_preview == "Where is order #4821?"
    event = db.scalar(select(WebhookEvent))
    assert (event.status, event.event_type, event.signature_valid) == ("processed", "message_created", True)

    # …and it is visible through the NEXUS API in NEXUS's own shape.
    inbox = connected_client.get("/api/conversations").json()
    assert inbox[0]["contact"]["name"] == "Lina Haddad"


def test_duplicate_delivery_is_not_processed_twice(connected_client, db):
    first = post(connected_client, webhook_message(), delivery_id="same-delivery")
    second = post(connected_client, webhook_message(), delivery_id="same-delivery")
    assert first.json()["result"] == "accepted"
    assert second.json()["result"] == "duplicate"
    assert (count(db, WebhookEvent), count(db, Conversation), count(db, Message)) == (1, 1, 1)


def test_same_message_via_two_deliveries_is_stored_once(connected_client, db):
    post(connected_client, webhook_message(), delivery_id="d-1")
    post(connected_client, {**webhook_message(), "event": "message_updated"}, delivery_id="d-2")
    assert (count(db, WebhookEvent), count(db, Message)) == (2, 1)


def test_other_accounts_are_ignored(connected_client, db):
    r = post(connected_client, webhook_message(account_id=999))
    assert r.json()["result"] == "ignored"
    assert count(db, Conversation) == 0


def test_conversation_status_change_updates_status(connected_client, db):
    post(connected_client, webhook_message(), delivery_id="d-1")
    payload = {**webhook_conversation(7, status="resolved"), "event": "conversation_status_changed"}
    assert post(connected_client, payload, delivery_id="d-2").json()["result"] == "accepted"
    db.expire_all()
    assert db.scalar(select(Conversation.status)) == "resolved"


def test_private_note_is_recorded_but_not_shown(connected_client, db):
    r = post(connected_client, webhook_message(private=True, message_type="outgoing"))
    assert r.json()["result"] == "ignored"
    assert count(db, Message) == 0


def test_malformed_payload_is_stored_as_failed(connected_client, db):
    payload = {"event": "message_created", "account": {"id": 1}, "id": 5, "message_type": "incoming"}  # no conversation
    r = post(connected_client, payload)
    assert r.json()["result"] == "failed"
    db.expire_all()
    event = db.scalar(select(WebhookEvent))
    assert event.status == "failed" and "conversation" in event.error
