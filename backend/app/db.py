from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# pool_pre_ping replaces stale pooled connections, e.g. after a Postgres restart.
engine = create_engine(str(settings.database_url), pool_pre_ping=True)

# expire_on_commit=False keeps loaded attributes readable after commit (e.g. for responses).
# Relationships that were never loaded are still unavailable once the session closes.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Request-scoped session, always closed after the request. It never commits: each write
# endpoint owns its transaction.
def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
