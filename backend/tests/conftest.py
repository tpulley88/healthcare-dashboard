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
from app.main import app


# Creates and migrates the test database once per run. Refuses any database not named
# *_test, so a misconfigured DATABASE_URL can't migrate or write to real data.
@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
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


# Each test runs inside a transaction that is rolled back afterwards. Endpoint commits become
# savepoint releases, so nothing persists and the no-delete trigger never gets in the way.
@pytest.fixture
def db() -> Iterator[Session]:
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
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def create_patient(client: TestClient) -> Callable[..., dict[str, Any]]:
    def _create(**overrides: Any) -> dict[str, Any]:
        body = {"first_name": "Ana", "last_name": "Ruiz", "date_of_birth": "1958-03-02"}
        response = client.post("/patients", json=body | overrides)
        assert response.status_code == 201, response.text
        return response.json()

    return _create
