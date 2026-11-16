"""Database connection.

We use SQLAlchemy's synchronous API: simpler to read for beginners, and FastAPI runs
sync endpoints in a thread pool so they don't block each other.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(
    get_settings().database_url(),
    pool_pre_ping=True,  # transparently replace connections the database has closed
    connect_args={"connect_timeout": 3},  # fail fast instead of hanging when the DB is down
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request, always closed afterwards."""
    with SessionLocal() as session:
        yield session


def check_database(session: Session) -> str:
    """Return "ok" if a trivial query succeeds, otherwise "unreachable"."""
    try:
        session.execute(text("SELECT 1"))
        return "ok"
    except SQLAlchemyError:
        session.rollback()
        return "unreachable"
