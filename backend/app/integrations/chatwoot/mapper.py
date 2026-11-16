"""Convert Chatwoot JSON into NEXUS's own shapes.

This is the ONLY place that knows Chatwoot's field names. Note that Chatwoot uses two
slightly different formats (checked against v4.19.1):

| Field          | REST API                    | Webhooks                       |
|----------------|-----------------------------|--------------------------------|
| message_type   | number (0 = incoming, 1 = outgoing, 2 = activity, 3 = template) | text ("incoming", …) |
| message time   | unix seconds                | ISO-8601 text                  |
| conversation id| `id` is the per-account display id in both                       |

Both are handled here so the rest of NEXUS never has to care.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SOURCE = "chatwoot"

_MESSAGE_TYPES = {0: "incoming", 1: "outgoing", 2: "activity", 3: "template"}
_MESSAGE_STATUSES = {0: "sent", 1: "delivered", 2: "read", 3: "failed"}
_CONVERSATION_STATUSES = {"open", "pending", "resolved", "snoozed"}
_CHANNELS = {"Channel::Api": "api", "Channel::WebWidget": "web", "Channel::Email": "email"}


@dataclass(frozen=True)
class NormalizedConversation:
    external_account_id: str
    external_id: str
    channel: str
    contact_name: str | None
    contact_email: str | None
    status: str
    last_activity_at: datetime
    last_message_preview: str | None


@dataclass(frozen=True)
class NormalizedMessage:
    external_id: str
    conversation_external_id: str
    direction: str  # inbound | outbound
    author_name: str | None
    body: str
    delivery_status: str  # pending | sent | delivered | failed
    created_at: datetime


class PayloadError(ValueError):
    """The Chatwoot data is missing something we need."""


def to_datetime(value: Any) -> datetime:
    """Accept unix seconds (int/float/str) or ISO-8601 text; always return an aware UTC datetime."""
    if value is None or value == "":
        raise PayloadError("missing timestamp")
    if isinstance(value, int | float) or (isinstance(value, str) and value.replace(".", "", 1).isdigit()):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    raise PayloadError(f"unrecognised timestamp: {value!r}")


def _channel(raw: Any) -> str:
    if not raw:
        return "unknown"
    return _CHANNELS.get(raw, str(raw).removeprefix("Channel::").lower())


def _message_type(raw: Any) -> str:
    return _MESSAGE_TYPES.get(raw, raw) if isinstance(raw, int) else str(raw)


def _delivery_status(raw: Any) -> str:
    status = _MESSAGE_STATUSES.get(raw, raw) if isinstance(raw, int) else (raw or "sent")
    return "delivered" if status == "read" else status if status in {"sent", "delivered", "failed"} else "sent"


def conversation(data: dict[str, Any], account_id: str) -> NormalizedConversation:
    """From a REST conversation item OR a webhook `conversation` object (same core fields)."""
    if data.get("id") is None:
        raise PayloadError("conversation without id")
    meta = data.get("meta") or {}
    sender = meta.get("sender") or {}
    status = data.get("status") if data.get("status") in _CONVERSATION_STATUSES else "open"

    # REST gives the latest real message here; webhooks give it in `messages`.
    last = data.get("last_non_activity_message") or next(iter(data.get("messages") or []), None) or {}
    activity = data.get("last_activity_at") or data.get("timestamp") or last.get("created_at")

    return NormalizedConversation(
        external_account_id=str(account_id),
        external_id=str(data["id"]),
        channel=_channel(meta.get("channel") or data.get("channel")),
        contact_name=sender.get("name") or None,
        contact_email=sender.get("email") or None,
        status=status,
        last_activity_at=to_datetime(activity) if activity else datetime.now(UTC),
        last_message_preview=(last.get("content") or None),
    )


def message(data: dict[str, Any], conversation_external_id: str | None = None) -> NormalizedMessage | None:
    """From a REST message OR a webhook message. Returns None for messages NEXUS doesn't show
    (private notes and activity events like "Conversation was resolved")."""
    kind = _message_type(data.get("message_type"))
    if kind not in {"incoming", "outgoing", "template"} or data.get("private"):
        return None
    if data.get("id") is None:
        raise PayloadError("message without id")

    conv_id = conversation_external_id or data.get("conversation_id") or (data.get("conversation") or {}).get("id")
    if conv_id is None:
        raise PayloadError("message without conversation id")

    sender = data.get("sender") or {}
    return NormalizedMessage(
        external_id=str(data["id"]),
        conversation_external_id=str(conv_id),
        direction="inbound" if kind == "incoming" else "outbound",
        author_name=sender.get("name") or None,
        body=data.get("content") or "",
        delivery_status=_delivery_status(data.get("status")),
        created_at=to_datetime(data.get("created_at")),
    )
