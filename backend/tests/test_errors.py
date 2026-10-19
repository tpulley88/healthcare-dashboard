import logging

from app.db import engine, get_db
from app.main import app

MARKER = "Failing row contains (Synthetic, Leakcheck, 1970-01-01)"


class BrokenSession:
    """A database session whose every call fails with a message quoting patient values."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise RuntimeError(MARKER)

        return fail


def test_unexpected_error_is_a_plain_500_without_patient_data_in_the_log(client, caplog):
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    with caplog.at_level(logging.INFO):
        response = client.get("/patients")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Leakcheck" not in caplog.text
    assert "Unhandled error on GET /patients: RuntimeError" in caplog.text


def test_database_errors_leave_out_submitted_values():
    assert engine.hide_parameters
