"""The app's "today" is the practice's calendar date, not the server's UTC date."""

from datetime import UTC, date, datetime

import pytest

from app import clock

# 02:00 UTC on Oct 18 is still 10 PM on Oct 17 in New York.
AFTER_UTC_MIDNIGHT = datetime(2026, 10, 18, 2, 0, tzinfo=UTC)
# 04:30 UTC on Oct 18 is 12:30 AM on Oct 18 in New York.
AFTER_LOCAL_MIDNIGHT = datetime(2026, 10, 18, 4, 30, tzinfo=UTC)


@pytest.fixture
def pin_clock(monkeypatch):
    def _pin(moment: datetime) -> None:
        monkeypatch.setattr(clock, "now", lambda: moment)

    return _pin


def test_practice_date_converts_to_practice_timezone():
    assert clock.practice_date(datetime(2026, 3, 2, 2, 0, tzinfo=UTC)) == date(2026, 3, 1)


@pytest.mark.parametrize(("moment", "age"), [(AFTER_UTC_MIDNIGHT, 25), (AFTER_LOCAL_MIDNIGHT, 26)])
def test_patient_and_summary_agree_on_age_around_midnight(
    client, create_patient, pin_clock, moment, age
):
    pin_clock(moment)
    patient = create_patient(date_of_birth="2000-10-18")

    fetched = client.get(f"/patients/{patient['id']}").json()
    summary = client.get(f"/patients/{patient['id']}/summary").json()

    assert fetched["age"] == age
    assert summary["age"] == age
    assert f"{age}-year-old" in summary["headline"]


def test_birth_date_is_in_the_future_until_local_midnight(client, create_patient, pin_clock):
    body = {"first_name": "Ana", "last_name": "Ruiz", "date_of_birth": "2026-10-18"}

    pin_clock(AFTER_UTC_MIDNIGHT)
    assert client.post("/patients", json=body).status_code == 422

    pin_clock(AFTER_LOCAL_MIDNIGHT)
    assert client.post("/patients", json=body).status_code == 201
