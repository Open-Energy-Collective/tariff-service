"""Database engine and session management.

Uses SQLite for MVP. Swap DATABASE_URL to PostgreSQL connection string
when real-time writes are needed — no application code changes required.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:  # type: ignore[misc]
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()
