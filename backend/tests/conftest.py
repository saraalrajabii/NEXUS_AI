"""Test setup.

Tests run against a SEPARATE database (nexus_test, created by
infra/nexus-db/init/01-create-test-database.sql) so they never touch your real data.
The schema is created by running the real Alembic migrations, which also tests them.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.config import Settings, get_settings
from app.db import get_db
from app.main import app

TEST_DB_NAME = os.environ.get("NEXUS_TEST_DB_NAME", "nexus_test")
BACKEND_DIR = Path(__file__).resolve().parent.parent


def make_test_settings(**overrides: object) -> Settings:
    """App settings for tests: test database, Chatwoot NOT configured unless overridden."""
    base = get_settings().model_dump()
    base.update(
        nexus_db_name=TEST_DB_NAME,
        chatwoot_base_url="",
        chatwoot_account_id="",
        chatwoot_api_token="",
        chatwoot_webhook_secret="",
    )
    base.update(overrides)
    return Settings(**base)


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_test_settings().database_url().render_as_string(hide_password=False)
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")  # start from an empty schema every run
    command.upgrade(cfg, "head")
    eng = create_engine(url)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session
        session.rollback()
        session.execute(text("TRUNCATE messages, conversations, webhook_events RESTART IDENTITY CASCADE"))
        session.commit()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: make_test_settings()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def connected_settings() -> Settings:
    """Settings with Chatwoot fully configured (pointing at the fake)."""
    from tests.chatwoot_fixtures import ACCOUNT_ID, SECRET

    return make_test_settings(
        chatwoot_base_url="http://chatwoot.test",
        chatwoot_account_id=ACCOUNT_ID,
        chatwoot_api_token="test-token",
        chatwoot_webhook_secret=SECRET,
    )


@pytest.fixture
def fake_chatwoot():
    from tests.chatwoot_fixtures import FakeChatwoot

    return FakeChatwoot()


@pytest.fixture
def connected_client(client: TestClient, fake_chatwoot) -> TestClient:
    """A test client whose backend is 'connected' to the fake Chatwoot."""
    from app.integrations.chatwoot.client import ChatwootClient
    from app.integrations.chatwoot.deps import get_chatwoot_factory

    app.dependency_overrides[get_settings] = connected_settings
    app.dependency_overrides[get_chatwoot_factory] = lambda: (
        lambda: ChatwootClient(connected_settings(), transport=fake_chatwoot.transport)
    )
    return client
