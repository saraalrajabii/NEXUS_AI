from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import CheckState


class DashboardSummaryOut(BaseModel):
    open_conversations: int
    events_today: int
    last_event_at: datetime | None
    integration_status: CheckState
