from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.db import get_db
from app.services.webhook_service import handle_chatwoot_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/chatwoot")
async def chatwoot_webhook(
    request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    """Called by Chatwoot, never by the frontend.

    We need the RAW body bytes: the signature is computed over exactly what Chatwoot sent,
    so parsing and re-serialising the JSON first would break verification.
    """
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    # The database work is synchronous, so run it in a worker thread.
    result, delivery_id = await run_in_threadpool(handle_chatwoot_webhook, db, settings, raw_body, headers)
    return {"result": result, "delivery_id": delivery_id}
