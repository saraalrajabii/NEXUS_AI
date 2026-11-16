"""NEXUS's own API shapes. These match docs/architecture.md §6 and frontend/src/types/api.ts.

They are intentionally independent of Chatwoot's response format — the integration
adapter converts Chatwoot data into these models.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models import Conversation

ConversationStatus = Literal["open", "pending", "resolved", "snoozed"]


class ContactOut(BaseModel):
    name: str | None
    email: str | None


class ConversationOut(BaseModel):
    id: uuid.UUID
    channel: str
    contact: ContactOut
    status: ConversationStatus
    last_message_preview: str | None
    last_activity_at: datetime

    @classmethod
    def from_model(cls, c: Conversation) -> "ConversationOut":
        return cls(
            id=c.id,
            channel=c.channel,
            contact=ContactOut(name=c.contact_name, email=c.contact_email),
            status=c.status,  # type: ignore[arg-type]  # guaranteed by a DB check constraint
            last_message_preview=c.last_message_preview,
            last_activity_at=c.last_activity_at,
        )


class ExternalRef(BaseModel):
    source: str
    account_id: str
    conversation_id: str


class ConversationDetailOut(ConversationOut):
    external_ref: ExternalRef

    @classmethod
    def from_model(cls, c: Conversation) -> "ConversationDetailOut":
        base = ConversationOut.from_model(c).model_dump()
        return cls(
            **base,
            external_ref=ExternalRef(source=c.source, account_id=c.external_account_id, conversation_id=c.external_id),
        )


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    direction: Literal["inbound", "outbound"]
    author_name: str | None
    body: str
    created_at: datetime
    delivery_status: Literal["pending", "sent", "delivered", "failed"]


class SyncOut(BaseModel):
    imported: int
    updated: int
    messages_imported: int


class ReplyIn(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]
