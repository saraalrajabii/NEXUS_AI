from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.integrations.chatwoot.client import chatwoot_status
from app.schemas.dashboard import DashboardSummaryOut
from app.services import inbox_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DashboardSummaryOut:
    open_count, events_today, last_event_at = inbox_service.dashboard_counts(db)
    return DashboardSummaryOut(
        open_conversations=open_count,
        events_today=events_today,
        last_event_at=last_event_at,
        integration_status=chatwoot_status(settings),
    )
