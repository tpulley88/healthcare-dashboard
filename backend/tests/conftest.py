from collections.abc import Callable, Iterator
from typing import Any

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.config import settings
from app.db import engine, get_db
from app.generated_summary import clear_cache, get_narrative_writer
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    """Create and migrate the test database once per run.

    The run stops unless the database name ends in _test,
    so a wrong DATABASE_URL can't migrate or change real data.
    """
    url = make_url(str(settings.database_url))
    if not url.database or not url.database.endswith("_test"):
        pytest.exit(f"Refusing to run: DATABASE_URL must name a *_test database ({url.database})")

    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def db() -> Iterator[Session]:
    """A session whose changes are all rolled back after the test.

    The test runs inside an outer transaction. When a route commits, it only closes a savepoint
    inside that transaction, and the rollback at the end discards everything.
    Tests never need to delete rows, which the no-delete trigger would block anyway.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """An API client whose routes use the test's rolled-back session.

    Generated summaries are off unless a test turns them on with a fake writer,
    so no test can reach the real service, even where an API key is set.
    """
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_narrative_writer] = lambda: None
    clear_cache()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def create_patient(client: TestClient) -> Callable[..., dict[str, Any]]:
    """Create a patient through the API. Keyword arguments override the default fields."""

    def _create(**overrides: Any) -> dict[str, Any]:
        body = {"first_name": "Ana", "last_name": "Ruiz", "date_of_birth": "1958-03-02"}
        response = client.post("/patients", json=body | overrides)
        assert response.status_code == 201, response.text
        return response.json()

    return _create
