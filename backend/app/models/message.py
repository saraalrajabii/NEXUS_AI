import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation

MESSAGE_DIRECTIONS = ("inbound", "outbound")
DELIVERY_STATUSES = ("pending", "sent", "delivered", "failed")


class Message(Base):
    """A message in a NEXUS conversation.

    (source, external_id) is unique: the same Chatwoot message can reach us by several
    paths (webhook, our own reply, a sync) but is stored only once.
    """

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        CheckConstraint(f"direction IN {MESSAGE_DIRECTIONS}", name="direction_valid"),
        CheckConstraint(f"delivery_status IN {DELIVERY_STATUSES}", name="delivery_status_valid"),
        Index(None, "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str] = mapped_column(String(16))
    author_name: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    delivery_status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
