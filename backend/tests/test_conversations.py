import uuid

from tests.factories import make_conversation, make_event, make_message


def test_empty_inbox(client):
    r = client.get("/api/conversations")
    assert r.status_code == 200
    assert r.json() == []


def test_list_is_newest_first_and_uses_nexus_shape(client, db):
    make_conversation(db, "1", minutes_ago=10)
    newest = make_conversation(db, "2", minutes_ago=1)
    data = client.get("/api/conversations").json()
    assert [c["id"] for c in data][0] == str(newest.id)
    assert set(data[0]) == {"id", "channel", "contact", "status", "last_message_preview", "last_activity_at"}
    assert data[0]["contact"] == {"name": "Customer 2", "email": "customer2@example.test"}


def test_status_filter(client, db):
    make_conversation(db, "1", status="open")
    make_conversation(db, "2", status="resolved")
    assert [c["status"] for c in client.get("/api/conversations?status=resolved").json()] == ["resolved"]


def test_invalid_status_uses_error_envelope(client):
    r = client.get("/api/conversations?status=banana")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_conversation_detail_has_external_ref(client, db):
    c = make_conversation(db, "42")
    r = client.get(f"/api/conversations/{c.id}")
    assert r.status_code == 200
    assert r.json()["external_ref"] == {"source": "chatwoot", "account_id": "1", "conversation_id": "42"}


def test_unknown_conversation_is_404_envelope(client):
    r = client.get(f"/api/conversations/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "NOT_FOUND", "message": "Conversation not found."}}


def test_messages_oldest_first(client, db):
    c = make_conversation(db)
    make_message(db, c, "m2", "second", minutes_ago=1)
    make_message(db, c, "m1", "first", minutes_ago=5)
    bodies = [m["body"] for m in client.get(f"/api/conversations/{c.id}/messages").json()]
    assert bodies == ["first", "second"]


def test_reply_without_chatwoot_credentials_is_503(client, db):
    c = make_conversation(db)
    r = client.post(f"/api/conversations/{c.id}/messages", json={"body": "Hi!"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CHATWOOT_NOT_CONFIGURED"


def test_empty_reply_is_rejected(client, db):
    c = make_conversation(db)
    r = client.post(f"/api/conversations/{c.id}/messages", json={"body": "   "})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_dashboard_summary(client, db):
    make_conversation(db, "1", status="open")
    make_conversation(db, "2", status="open")
    make_conversation(db, "3", status="resolved")
    make_event(db, "d-1")
    make_event(db, "d-2")
    data = client.get("/api/dashboard/summary").json()
    assert data["open_conversations"] == 2
    assert data["events_today"] == 2
    assert data["last_event_at"] is not None
    assert data["integration_status"] == "not_configured"


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
