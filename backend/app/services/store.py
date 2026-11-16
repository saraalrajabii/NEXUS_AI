"""Save normalized Chatwoot data into NEXUS tables — idempotently.

"Upsert" = INSERT, or UPDATE if a row with the same external id already exists.
The unique constraints from Milestone 3 decide what "the same" means, so storing the
same message twice (webhook + reply + sync) always ends with exactly one row.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.integrations.chatwoot.mapper import SOURCE, NormalizedConversation, NormalizedMessage
from app.models import Conversation, Message


def upsert_conversation(db: Session, c: NormalizedConversation) -> tuple[uuid.UUID, bool]:
    """Returns (NEXUS conversation id, True if it was newly created)."""
    values = {
        "source": SOURCE,
        "external_account_id": c.external_account_id,
        "external_id": c.external_id,
        "channel": c.channel,
        "contact_name": c.contact_name,
        "contact_email": c.contact_email,
        "status": c.status,
        "last_activity_at": c.last_activity_at,
    }
    if c.last_message_preview is not None:
        values["last_message_preview"] = c.last_message_preview

    existing = db.scalar(
        select(Conversation.id).where(
            Conversation.source == SOURCE,
            Conversation.external_account_id == c.external_account_id,
            Conversation.external_id == c.external_id,
        )
    )
    update = {k: v for k, v in values.items() if k not in {"source", "external_account_id", "external_id"}}
    stmt = (
        insert(Conversation)
        .values(id=uuid.uuid4(), **values)
        .on_conflict_do_update(constraint="uq_conversations_source_external_account_id_external_id", set_=update)
        .returning(Conversation.id)
    )
    conversation_id = db.execute(stmt).scalar_one()
    return conversation_id, existing is None


def upsert_message(db: Session, conversation_id: uuid.UUID, m: NormalizedMessage) -> tuple[uuid.UUID, bool]:
    """Returns (NEXUS message id, True if it was newly created). Also refreshes the conversation preview."""
    existing = db.scalar(select(Message.id).where(Message.source == SOURCE, Message.external_id == m.external_id))
    stmt = (
        insert(Message)
        .values(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            source=SOURCE,
            external_id=m.external_id,
            direction=m.direction,
            author_name=m.author_name,
            body=m.body,
            delivery_status=m.delivery_status,
            created_at=m.created_at,
        )
        # Same message again → keep one row, only refresh what can change.
        .on_conflict_do_update(
            constraint="uq_messages_source_external_id",
            set_={"body": m.body, "delivery_status": m.delivery_status},
        )
        .returning(Message.id)
    )
    message_id = db.execute(stmt).scalar_one()

    # populate_existing: re-read from the database, the upsert above bypassed the session cache.
    conversation = db.get(Conversation, conversation_id, populate_existing=True)
    if conversation is not None:
        if m.created_at >= conversation.last_activity_at:
            conversation.last_activity_at = m.created_at
            conversation.last_message_preview = m.body
        elif conversation.last_message_preview is None:
            conversation.last_message_preview = m.body  # better an older preview than none
    return message_id, existing is None
