from datetime import UTC, datetime

from app.integrations.chatwoot import mapper
from tests.chatwoot_fixtures import NOW, rest_conversation, rest_message, webhook_conversation, webhook_message


def test_webhook_message_text_type_and_iso_time():
    m = mapper.message(webhook_message())
    assert m is not None
    assert m.direction == "inbound"
    assert m.external_id == "101"
    assert m.conversation_external_id == "7"
    assert m.created_at == datetime.fromtimestamp(NOW, tz=UTC)


def test_iso_timestamp_with_milliseconds_and_z():
    assert mapper.to_datetime("2026-11-16T20:15:00.000Z") == datetime(2026, 11, 16, 20, 15, tzinfo=UTC)


def test_preview_filled_even_by_an_older_message(db):
    from app.services.store import upsert_conversation, upsert_message

    conv_id, _ = upsert_conversation(db, mapper.conversation({**webhook_conversation(7), "last_activity_at": NOW + 600}, "1"))
    older = mapper.message({**webhook_message(), "created_at": NOW - 600})
    upsert_message(db, conv_id, older)
    db.commit()
    from app.models import Conversation

    assert db.get(Conversation, conv_id, populate_existing=True).last_message_preview == older.body


def test_rest_message_numeric_type_and_unix_time():
    m = mapper.message(rest_message(5, "Thanks!", message_type=1), "7")
    assert m is not None
    assert m.direction == "outbound"
    assert m.created_at.tzinfo is not None


def test_private_notes_and_activity_messages_are_skipped():
    assert mapper.message(webhook_message(private=True)) is None
    assert mapper.message(rest_message(6, "Conversation was resolved", message_type=2), "7") is None


def test_conversation_from_webhook_and_rest_have_same_shape():
    w = mapper.conversation(webhook_conversation(7), "1")
    r = mapper.conversation(rest_conversation(8), "1")
    assert (w.external_id, w.channel, w.contact_name, w.status) == ("7", "api", "Lina Haddad", "open")
    assert (r.external_id, r.channel, r.last_message_preview) == ("8", "api", "Hello")


def test_read_status_maps_to_delivered():
    assert mapper.message({**rest_message(1, "x"), "status": 2}, "7").delivery_status == "delivered"
