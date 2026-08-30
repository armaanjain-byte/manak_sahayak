
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings

class Base(DeclarativeBase):
    pass


_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url)
    return _engine


def init_db() -> None:
    """Create database tables for local/dev startup."""
    Base.metadata.create_all(get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = Session(bind=get_engine())
    try:
        yield db
    finally:
        db.close()
