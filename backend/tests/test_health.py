from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.main import app
from tests.conftest import make_test_settings


def test_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_database_ok_chatwoot_not_configured(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "degraded", "checks": {"database": "ok", "chatwoot": "not_configured"}}


def test_ready_reports_unreachable_chatwoot(client):
    # Configured, but nothing listens on this port → "unreachable", backend keeps working.
    app.dependency_overrides[get_settings] = lambda: make_test_settings(
        chatwoot_base_url="http://127.0.0.1:9", chatwoot_account_id="1", chatwoot_api_token="x"
    )
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"] == {"database": "ok", "chatwoot": "unreachable"}


def _use_unreachable_database():
    bad = create_engine("postgresql+psycopg://nobody:x@127.0.0.1:1/none", connect_args={"connect_timeout": 1})

    def broken_db():
        with Session(bad) as s:
            yield s

    app.dependency_overrides[get_db] = broken_db


def test_ready_database_down_returns_503(client):
    _use_unreachable_database()
    r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["checks"]["database"] == "unreachable"
    assert r.json()["status"] == "degraded"


def test_data_endpoints_report_database_unavailable(client):
    _use_unreachable_database()
    r = client.get("/api/conversations")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    # Liveness doesn't depend on the database.
    assert client.get("/health/live").status_code == 200
