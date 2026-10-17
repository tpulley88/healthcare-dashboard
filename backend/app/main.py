"""FastAPI application: routes, startup checks, and shutdown cleanup.

Routes are plain `def` functions rather than `async def`.
FastAPI runs them in a thread pool, so their blocking database calls don't hold up other requests.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Importing the engine also loads the settings, so missing configuration stops startup.
from app.db import engine
from app.log_filters import DropQueryString
from app.routers import notes, patients


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Close pooled database connections when the server shuts down."""
    yield
    engine.dispose()


# Keep patient names out of the access log by removing query strings.
# uvicorn sets up its loggers before importing this module, so the filter stays in place.
logging.getLogger("uvicorn.access").addFilter(DropQueryString())

app = FastAPI(title="Healthcare Dashboard API", lifespan=lifespan)
app.include_router(patients.router)
app.include_router(notes.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the server is running.

    This is a liveness check only and doesn't contact the database.
    A database outage shouldn't make the API process look dead and get it restarted.
    """
    return {"status": "ok"}
