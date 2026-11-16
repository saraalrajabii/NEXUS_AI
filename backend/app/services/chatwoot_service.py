"""Operations that call Chatwoot's API: sync (pull) and reply (push)."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.errors import NexusError
from app.integrations.chatwoot import mapper
from app.integrations.chatwoot.client import ChatwootClient
from app.models import Message
from app.services.inbox_service import get_conversation
from app.services.store import upsert_conversation, upsert_message

log = logging.getLogger("nexus.chatwoot")


def sync_conversations(db: Session, client: ChatwootClient) -> dict[str, int]:
    """Pull every conversation and its recent messages from Chatwoot.

    Used to backfill history (webhooks only report what happens AFTER they're set up)
    and to recover from missed webhooks. Safe to run any number of times.
    """
    counts = {"imported": 0, "updated": 0, "messages_imported": 0}
    for item in client.list_conversations():
        normalized = mapper.conversation(item, client.account_id)
        conversation_id, created = upsert_conversation(db, normalized)
        counts["imported" if created else "updated"] += 1
        for raw in client.list_messages(normalized.external_id):
            m = mapper.message(raw, normalized.external_id)
            if m is not None and upsert_message(db, conversation_id, m)[1]:
                counts["messages_imported"] += 1
        db.commit()
    log.info("Sync finished: %s", counts)
    return counts


def send_reply(db: Session, client: ChatwootClient, conversation_id: uuid.UUID, body: str) -> Message:
    """Send through Chatwoot FIRST, store second.

    If Chatwoot fails, nothing is stored and the agent sees an error (their text is kept in the UI).
    The stored row uses Chatwoot's message id, so the webhook Chatwoot sends for this same reply
    updates this row instead of creating a duplicate.
    """
    conversation = get_conversation(db, conversation_id)
    if conversation.source != mapper.SOURCE:
        raise NexusError("VALIDATION_ERROR", "This conversation is not connected to Chatwoot.", 422)

    created = client.create_message(conversation.external_id, body)
    normalized = mapper.message(created, conversation.external_id)
    if normalized is None:  # pragma: no cover - Chatwoot always returns an outgoing message here
        raise NexusError("CHATWOOT_REJECTED", "Chatwoot did not return the sent message.", 502)

    message_id, _ = upsert_message(db, conversation.id, normalized)
    db.commit()
    message = db.get(Message, message_id)
    assert message is not None
    return message
