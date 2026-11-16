"""NEXUS Backend entry point. Run with: uvicorn app.main:app"""

import logging

from fastapi import FastAPI

from app.api import conversations, dashboard, health, webhooks
from app.config import get_settings
from app.errors import register_error_handlers

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
)
log = logging.getLogger("nexus")

app = FastAPI(
    title="NEXUS Backend",
    version="0.1.0",
    description="API for the NEXUS support workspace. The frontend talks only to this service.",
)
register_error_handlers(app)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(conversations.router)
app.include_router(webhooks.router)

# Report configuration at startup — which settings are present, never their values.
log.info(
    "NEXUS backend starting (database=%s@%s:%s/%s, chatwoot_api=%s, webhook_secret=%s)",
    settings.nexus_db_user,
    settings.nexus_db_host,
    settings.nexus_db_port,
    settings.nexus_db_name,
    "configured" if settings.chatwoot_api_configured else "NOT configured",
    "set" if settings.chatwoot_webhook_secret.get_secret_value() else "NOT set",
)
