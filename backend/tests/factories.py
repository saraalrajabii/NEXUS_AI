"""Helpers to insert test rows directly (no Chatwoot needed)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Conversation, Message, WebhookEvent


def make_conversation(db: Session, external_id: str = "1", status: str = "open", minutes_ago: int = 0) -> Conversation:
    c = Conversation(
        source="chatwoot",
        external_account_id="1",
        external_id=external_id,
        channel="api",
        contact_name=f"Customer {external_id}",
        contact_email=f"customer{external_id}@example.test",
        status=status,
        last_message_preview="Hello",
        last_activity_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    db.add(c)
    db.commit()
    return c


def make_message(db: Session, conversation: Conversation, external_id: str, body: str, minutes_ago: int = 0) -> Message:
    m = Message(
        conversation_id=conversation.id,
        source="chatwoot",
        external_id=external_id,
        direction="inbound",
        author_name=conversation.contact_name,
        body=body,
        delivery_status="delivered",
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    db.add(m)
    db.commit()
    return m


def make_event(db: Session, delivery_id: str, event_type: str = "message_created") -> WebhookEvent:
    e = WebhookEvent(
        source="chatwoot",
        delivery_id=delivery_id,
        event_type=event_type,
        payload={"event": event_type},
        signature_valid=True,
    )
    db.add(e)
    db.commit()
    return e
