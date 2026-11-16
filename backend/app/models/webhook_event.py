from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Identity, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

WEBHOOK_EVENT_STATUSES = ("received", "processed", "failed", "ignored")


class WebhookEvent(Base):
    """Every webhook delivery we accepted — an audit log AND our duplicate filter.

    (source, delivery_id) is unique, so if Chatwoot delivers the same event twice,
    the second insert is rejected by the database itself.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("source", "delivery_id"),
        CheckConstraint(f"status IN {WEBHOOK_EVENT_STATUSES}", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    delivery_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    signature_valid: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'received'"))
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
