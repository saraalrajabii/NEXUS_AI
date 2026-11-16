import uuid
from contextlib import closing

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.integrations.chatwoot.deps import ChatwootFactory, get_chatwoot_factory
from app.schemas.conversations import (
    ConversationDetailOut,
    ConversationOut,
    ConversationStatus,
    MessageOut,
    ReplyIn,
    SyncOut,
)
from app.services import chatwoot_service, inbox_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    status: ConversationStatus | None = Query(default=None), db: Session = Depends(get_db)
) -> list[ConversationOut]:
    return [ConversationOut.from_model(c) for c in inbox_service.list_conversations(db, status)]


@router.post("/sync", response_model=SyncOut)
def sync_conversations(
    db: Session = Depends(get_db), chatwoot: ChatwootFactory = Depends(get_chatwoot_factory)
) -> SyncOut:
    """Pull conversations + recent messages from Chatwoot's API (backfill / recovery)."""
    with closing(chatwoot()) as client:
        return SyncOut(**chatwoot_service.sync_conversations(db, client))


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)) -> ConversationDetailOut:
    return ConversationDetailOut.from_model(inbox_service.get_conversation(db, conversation_id))


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: uuid.UUID, db: Session = Depends(get_db)) -> list[MessageOut]:
    return [MessageOut.model_validate(m) for m in inbox_service.list_messages(db, conversation_id)]


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_reply(
    conversation_id: uuid.UUID,
    reply: ReplyIn,
    db: Session = Depends(get_db),
    chatwoot: ChatwootFactory = Depends(get_chatwoot_factory),
) -> MessageOut:
    inbox_service.get_conversation(db, conversation_id)  # 404 before anything else
    with closing(chatwoot()) as client:
        return MessageOut.model_validate(chatwoot_service.send_reply(db, client, conversation_id, reply.body))
