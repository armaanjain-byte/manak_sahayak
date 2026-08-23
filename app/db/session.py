
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

class Base(DeclarativeBase):
    pass

def get_session() -> None:
    pass

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    from app.config import get_settings
    engine = create_engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()
