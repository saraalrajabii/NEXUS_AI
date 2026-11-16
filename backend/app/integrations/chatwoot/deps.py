"""FastAPI dependency that gives routes a way to open a Chatwoot client.

It returns a *factory* (not a client) so a route can first validate its input and check
the conversation exists — returning 422/404 for bad requests — and only then require
Chatwoot credentials (503 CHATWOOT_NOT_CONFIGURED). Tests override this to plug in a fake Chatwoot.
"""

from collections.abc import Callable

from fastapi import Depends

from app.config import Settings, get_settings
from app.integrations.chatwoot.client import ChatwootClient

ChatwootFactory = Callable[[], ChatwootClient]


def get_chatwoot_factory(settings: Settings = Depends(get_settings)) -> ChatwootFactory:
    return lambda: ChatwootClient(settings)  # raises CHATWOOT_NOT_CONFIGURED if credentials are missing
