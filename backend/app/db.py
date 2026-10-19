"""Database engine and per-request sessions.

Transaction ownership: get_db never commits.
Each route that changes data calls db.commit() itself, once its work is complete.
If a route fails before committing, closing the session discards its changes.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Test each pooled connection before use.
# Connections broken by a Postgres restart are replaced instead of failing a request.
# hide_parameters keeps submitted values out of error messages. Postgres's own error detail
# can still include a failing row, so main.py never logs error messages at all.
engine = create_engine(str(settings.database_url), pool_pre_ping=True, hide_parameters=True)

# Keep loaded values readable after a commit, so a route can save an object and return it.
# Relationships that were never loaded still can't be read once the session is closed.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Provide one database session per request, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
