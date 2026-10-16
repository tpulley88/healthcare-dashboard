import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Importing the engine loads settings, so missing configuration fails at startup.
from app.db import engine
from app.log_filters import DropQueryString
from app.routers import patients


# Close pooled database connections cleanly on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


# uvicorn configures its loggers before importing the app, so this filter persists.
logging.getLogger("uvicorn.access").addFilter(DropQueryString())

app = FastAPI(title="Healthcare Dashboard API", lifespan=lifespan)
app.include_router(patients.router)


# Liveness only: reports that the process is serving, not that the database is reachable.
# Endpoints are sync `def` so blocking SQLAlchemy calls run in FastAPI's threadpool.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
