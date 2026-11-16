"""Chatwoot REST API client (Application API, authenticated with an agent access token).

Failure rules:
  * Every call has a timeout, so a slow Chatwoot can't hang NEXUS.
  * GET requests are retried once on network errors / 5xx (safe: reading twice changes nothing).
  * POST requests are NEVER retried automatically — retrying "send reply" after a timeout could
    send the customer the same message twice.
  * Errors become NexusErrors with stable codes; tokens never appear in logs or messages.
"""

import logging
from typing import Any

import httpx

from app.config import Settings
from app.errors import NexusError
from app.schemas.common import CheckState

log = logging.getLogger("nexus.chatwoot")

MAX_CONVERSATION_PAGES = 20  # 25 per page → up to 500 conversations per sync (plenty for Lesson 01)


def not_configured() -> NexusError:
    return NexusError(
        "CHATWOOT_NOT_CONFIGURED",
        "Chatwoot credentials are missing. Set CHATWOOT_BASE_URL, CHATWOOT_ACCOUNT_ID and CHATWOOT_API_TOKEN.",
        503,
    )


class ChatwootClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        if not settings.chatwoot_api_configured:
            raise not_configured()
        self.account_id = settings.chatwoot_account_id.strip()
        self._http = httpx.Client(
            base_url=settings.chatwoot_base_url.rstrip("/"),
            headers={"api_access_token": settings.chatwoot_api_token.get_secret_value(), "Accept": "application/json"},
            timeout=settings.chatwoot_timeout_seconds,
            transport=transport,
        )

    # ── low level ────────────────────────────────────────────────────────────
    def _request(self, method: str, path: str, *, retry: bool, **kwargs: Any) -> Any:
        attempts = 2 if retry else 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._http.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                log.warning("Chatwoot %s %s failed (attempt %s/%s): %s", method, path, attempt, attempts, type(exc).__name__)
                if attempt < attempts:
                    continue
                raise NexusError("CHATWOOT_UNAVAILABLE", "Chatwoot did not respond. Try again shortly.", 502) from exc

            if response.status_code >= 500 and attempt < attempts:
                log.warning("Chatwoot %s %s returned %s, retrying", method, path, response.status_code)
                continue
            return self._handle(method, path, response)
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _handle(method: str, path: str, response: httpx.Response) -> Any:
        status = response.status_code
        if status in (401, 403):
            log.error("Chatwoot rejected the API token (%s %s → %s)", method, path, status)
            raise NexusError("CHATWOOT_AUTH_FAILED", "Chatwoot rejected the API token. Check CHATWOOT_API_TOKEN.", 502)
        if status == 404:
            raise NexusError("CHATWOOT_NOT_FOUND", "Chatwoot could not find that resource.", 502)
        if status >= 500:
            log.error("Chatwoot %s %s → %s", method, path, status)
            raise NexusError("CHATWOOT_UNAVAILABLE", f"Chatwoot returned an error (HTTP {status}).", 502)
        if status >= 400:
            log.error("Chatwoot %s %s → %s: %s", method, path, status, response.text[:300])
            raise NexusError("CHATWOOT_REJECTED", f"Chatwoot refused the request (HTTP {status}).", 502)
        try:
            return response.json()
        except ValueError as exc:
            raise NexusError("CHATWOOT_UNAVAILABLE", "Chatwoot sent an unreadable response.", 502) from exc

    # ── API calls ────────────────────────────────────────────────────────────
    def _account_path(self, suffix: str) -> str:
        return f"/api/v1/accounts/{self.account_id}{suffix}"

    def check_profile(self) -> None:
        """Cheap authenticated call: proves the URL and token both work."""
        self._request("GET", "/api/v1/profile", retry=False)

    def list_conversations(self) -> list[dict[str, Any]]:
        """All conversations in every status (paginated, 25 per page)."""
        items: list[dict[str, Any]] = []
        for page in range(1, MAX_CONVERSATION_PAGES + 1):
            data = self._request("GET", self._account_path("/conversations"), retry=True,
                                 params={"status": "all", "page": page})
            batch = (data.get("data") or {}).get("payload") or []
            items.extend(batch)
            if len(batch) < 25:
                break
        return items

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """Most recent messages of a conversation (Chatwoot returns the latest 20 by default)."""
        data = self._request("GET", self._account_path(f"/conversations/{conversation_id}/messages"), retry=True)
        return data.get("payload") or []

    def create_message(self, conversation_id: str, content: str) -> dict[str, Any]:
        """Send an agent reply. Not retried (see module docstring)."""
        return self._request(
            "POST",
            self._account_path(f"/conversations/{conversation_id}/messages"),
            retry=False,
            json={"content": content, "message_type": "outgoing", "private": False},
        )

    def close(self) -> None:
        self._http.close()


def chatwoot_status(settings: Settings, transport: httpx.BaseTransport | None = None) -> CheckState:
    """For /health/ready: not_configured | unreachable | error (e.g. bad token) | ok."""
    if not settings.chatwoot_api_configured:
        return "not_configured"
    client = ChatwootClient(settings, transport)
    try:
        client.check_profile()
        return "ok"
    except NexusError as exc:
        return "unreachable" if exc.code == "CHATWOOT_UNAVAILABLE" else "error"
    finally:
        client.close()
