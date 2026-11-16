"""Receive a Chatwoot webhook: verify → de-duplicate → store → apply.

    1. Verify the HMAC signature and timestamp  (reject forgeries and replays)
    2. Record the delivery in webhook_events    (a repeat delivery_id is a no-op → "duplicate")
    3. Convert the payload with the mapper      (Chatwoot JSON → NEXUS models)
    4. Upsert conversations / messages          (idempotent, see services/store.py)
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import NexusError
from app.integrations.chatwoot import mapper
from app.integrations.chatwoot.signature import SignatureError, verify_signature
from app.models import WebhookEvent
from app.services.store import upsert_conversation, upsert_message

log = logging.getLogger("nexus.webhooks")

MESSAGE_EVENTS = {"message_created", "message_updated"}
CONVERSATION_EVENTS = {"conversation_created", "conversation_updated", "conversation_status_changed"}

Result = Literal["accepted", "duplicate", "ignored", "failed"]


def handle_chatwoot_webhook(
    db: Session, settings: Settings, raw_body: bytes, headers: dict[str, str]
) -> tuple[Result, str]:
    """Returns (result, delivery_id). Raises NexusError for requests we refuse outright."""
    secret = settings.chatwoot_webhook_secret.get_secret_value()
    if not secret:
        # Fail closed: without a secret we cannot tell real webhooks from fake ones.
        raise NexusError("WEBHOOK_NOT_CONFIGURED", "CHATWOOT_WEBHOOK_SECRET is not set; webhooks are refused.", 503)

    try:
        verify_signature(
            secret=secret,
            raw_body=raw_body,
            timestamp=headers.get("x-chatwoot-timestamp"),
            signature=headers.get("x-chatwoot-signature"),
        )
    except SignatureError as exc:
        # Unauthenticated requests are NOT stored (anyone could otherwise fill our database).
        log.warning("Rejected webhook: %s", exc)
        raise NexusError("INVALID_SIGNATURE", "Webhook signature check failed.", 401) from exc

    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except ValueError as exc:
        raise NexusError("VALIDATION_ERROR", "Webhook body is not valid JSON.", 422) from exc

    event_type = str(payload.get("event") or "unknown")
    # Chatwoot sends a unique X-Chatwoot-Delivery id; if it's ever missing, fall back to a hash
    # of the body so an identical repeat is still recognised.
    delivery_id = headers.get("x-chatwoot-delivery") or "sha256:" + hashlib.sha256(raw_body).hexdigest()

    # ── 2. de-duplicate: INSERT … ON CONFLICT DO NOTHING ──────────────────────
    event_id = db.execute(
        insert(WebhookEvent)
        .values(
            source=mapper.SOURCE,
            delivery_id=delivery_id,
            event_type=event_type,
            payload=payload,
            signature_valid=True,
        )
        .on_conflict_do_nothing(constraint="uq_webhook_events_source_delivery_id")
        .returning(WebhookEvent.id)
    ).scalar_one_or_none()
    if event_id is None:
        db.rollback()
        log.info("Duplicate webhook delivery %s (%s) ignored", delivery_id, event_type)
        return "duplicate", delivery_id
    db.commit()  # the delivery is recorded even if applying it fails below

    # ── 3–4. apply ───────────────────────────────────────────────────────────
    event = db.get(WebhookEvent, event_id)
    assert event is not None
    try:
        status = _apply(db, settings, event_type, payload)
        event.status = status
        event.processed_at = datetime.now(UTC)
        db.commit()
        log.info("Webhook %s (%s) → %s", delivery_id, event_type, status)
        return ("accepted" if status == "processed" else "ignored"), delivery_id
    except Exception as exc:  # store the failure for inspection, don't lose the event
        db.rollback()
        event = db.get(WebhookEvent, event_id)
        assert event is not None
        event.status = "failed"
        event.error = f"{type(exc).__name__}: {exc}"[:2000]
        event.processed_at = datetime.now(UTC)
        db.commit()
        log.exception("Webhook %s (%s) failed to apply", delivery_id, event_type)
        return "failed", delivery_id


def _apply(db: Session, settings: Settings, event_type: str, payload: dict[str, Any]) -> str:
    account_id = str((payload.get("account") or {}).get("id", ""))
    if account_id != settings.chatwoot_account_id.strip():
        log.info("Ignoring %s for account %r (we sync account %r)", event_type, account_id, settings.chatwoot_account_id)
        return "ignored"

    if event_type in CONVERSATION_EVENTS:
        upsert_conversation(db, mapper.conversation(payload, account_id))
        return "processed"

    if event_type in MESSAGE_EVENTS:
        conv_data = payload.get("conversation") or {}
        normalized_message = mapper.message(payload, str(conv_data.get("id", "")) or None)
        conversation_id, _ = upsert_conversation(db, mapper.conversation(conv_data, account_id))
        if normalized_message is None:  # private note / activity message
            return "ignored"
        upsert_message(db, conversation_id, normalized_message)
        return "processed"

    return "ignored"
