from typing import Literal

from pydantic import BaseModel

from app.schemas.common import CheckState


class LiveOut(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessChecks(BaseModel):
    database: CheckState
    chatwoot: CheckState


class ReadinessOut(BaseModel):
    status: Literal["ok", "degraded"]
    checks: ReadinessChecks
