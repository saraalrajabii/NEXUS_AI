from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import check_database, get_db
from app.integrations.chatwoot.client import chatwoot_status
from app.schemas.health import LiveOut, ReadinessChecks, ReadinessOut

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveOut)
def live() -> LiveOut:
    """Is the backend process running? (No dependencies checked.)"""
    return LiveOut()


@router.get("/health/ready", response_model=ReadinessOut)
def ready(response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReadinessOut:
    """Can the backend do its job? 200 = it can serve requests (maybe degraded); 503 = database down."""
    checks = ReadinessChecks(database=check_database(db), chatwoot=chatwoot_status(settings))
    if checks.database != "ok":
        response.status_code = 503
    status = "ok" if checks.database == "ok" and checks.chatwoot == "ok" else "degraded"
    return ReadinessOut(status=status, checks=checks)
