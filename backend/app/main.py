from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Importing the engine loads settings, so missing configuration fails at startup.
from app.db import engine


# Close pooled database connections cleanly on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(title="Healthcare Dashboard API", lifespan=lifespan)


# Liveness only: reports that the process is serving, not that the database is reachable.
# Endpoints are sync `def` so blocking SQLAlchemy calls run in FastAPI's threadpool.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
