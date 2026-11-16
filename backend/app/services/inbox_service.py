"""Inbox business logic: reads NEXUS's own tables. Never touches Chatwoot's database."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import Conversation, Message, WebhookEvent


def list_conversations(db: Session, status: str | None) -> list[Conversation]:
    query = select(Conversation).order_by(Conversation.last_activity_at.desc())
    if status:
        query = query.where(Conversation.status == status)
    return list(db.scalars(query))


def get_conversation(db: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise not_found("Conversation")
    return conversation


def list_messages(db: Session, conversation_id: uuid.UUID) -> list[Message]:
    get_conversation(db, conversation_id)  # 404 if the conversation doesn't exist
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    return list(db.scalars(query))


def dashboard_counts(db: Session) -> tuple[int, int, datetime | None]:
    """(open conversations, webhook events since midnight UTC, time of the latest event)."""
    open_count = db.scalar(select(func.count()).select_from(Conversation).where(Conversation.status == "open"))
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    events_today = db.scalar(
        select(func.count()).select_from(WebhookEvent).where(WebhookEvent.received_at >= midnight)
    )
    last_event_at = db.scalar(select(func.max(WebhookEvent.received_at)))
    return open_count or 0, events_today or 0, last_event_at
