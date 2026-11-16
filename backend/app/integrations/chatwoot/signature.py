"""Verify that a webhook really came from Chatwoot.

Chatwoot (v4.19.1, lib/webhooks/trigger.rb) signs every webhook that has a secret:

    X-Chatwoot-Timestamp: <unix seconds>
    X-Chatwoot-Signature: sha256=<hex HMAC-SHA256(secret, "<timestamp>.<raw body>")>

Only someone who knows the secret can produce a valid signature, and including the
timestamp lets us reject old requests that an attacker might "replay".
"""

import hashlib
import hmac
import time

DEFAULT_MAX_AGE_SECONDS = 300  # 5 minutes


class SignatureError(Exception):
    """Why a webhook was rejected (safe to log; never contains the secret)."""


def compute_signature(secret: str, timestamp: str, raw_body: bytes) -> str:
    message = timestamp.encode() + b"." + raw_body
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(
    *,
    secret: str,
    raw_body: bytes,
    timestamp: str | None,
    signature: str | None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> None:
    """Raise SignatureError unless the request is authentic and recent."""
    if not timestamp or not signature:
        raise SignatureError("missing X-Chatwoot-Timestamp or X-Chatwoot-Signature header")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise SignatureError("timestamp is not a number") from exc

    age = (time.time() if now is None else now) - sent_at
    if abs(age) > max_age_seconds:
        raise SignatureError(f"timestamp outside the allowed window ({int(age)}s old)")

    expected = compute_signature(secret, timestamp, raw_body)
    # compare_digest takes the same time whether the first or last character differs,
    # so an attacker can't guess the signature one character at a time.
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("signature does not match")
