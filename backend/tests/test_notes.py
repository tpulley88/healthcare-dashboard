import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Note
from tests.helpers import MISSING_ID, error_fields


@pytest.fixture
def patient(create_patient):
    return create_patient(date_of_birth="1958-03-02")


@pytest.fixture
def create_note(client):
    def _create(patient_id, taken_at="2026-09-20T09:30:00-04:00", content="BP follow-up."):
        response = client.post(
            f"/patients/{patient_id}/notes", json={"taken_at": taken_at, "content": content}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


def notes_url(patient_id):
    return f"/patients/{patient_id}/notes"


def post_note(client, patient_id, **body):
    return client.post(notes_url(patient_id), json=body)


# --- Create ----------------------------------------------------------------------------------


def test_create_note(create_note, patient):
    note = create_note(patient["id"], taken_at="2026-09-20T09:30:00-04:00")
    assert note["patient_id"] == patient["id"]
    assert datetime.fromisoformat(note["taken_at"]) == datetime(2026, 9, 20, 13, 30, tzinfo=UTC)
    assert {"id", "created_at"} <= note.keys()
    assert "deleted_at" not in note


def test_create_note_trims_edges_and_keeps_line_breaks(create_note, patient):
    note = create_note(patient["id"], content="\n  Line one.\n\nLine two.  \n")
    assert note["content"] == "Line one.\n\nLine two."


def test_create_note_accepts_maximum_length(create_note, patient):
    assert len(create_note(patient["id"], content="x" * 10_000)["content"]) == 10_000


def test_create_note_allows_small_clock_skew(create_note, patient):
    create_note(patient["id"], taken_at=(datetime.now(UTC) + timedelta(minutes=1)).isoformat())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content", " \n\t "),
        ("content", "x" * 10_001),
        ("taken_at", "2026-09-20T09:30:00"),
        ("taken_at", (datetime.now(UTC) + timedelta(minutes=10)).isoformat()),
        ("taken_at", "1950-01-01T09:00:00-05:00"),
        ("taken_at", "not-a-date"),
    ],
)
def test_create_note_rejects_invalid_field(client, patient, field, value):
    body = {"taken_at": "2026-09-20T09:30:00-04:00", "content": "Seen.", field: value}
    assert error_fields(post_note(client, patient["id"], **body)) == {field}


def test_create_note_rejects_missing_and_unknown_fields(client, patient):
    response = post_note(client, patient["id"], deleted_at=None)
    assert error_fields(response) == {"taken_at", "content", "deleted_at"}


# Birth date is compared with the note's calendar date in the practice timezone.
def test_create_note_on_birth_date_is_allowed(create_note, patient):
    create_note(patient["id"], taken_at="1958-03-02T23:00:00-05:00")


def test_create_note_for_unknown_patient_is_404(client):
    response = post_note(client, MISSING_ID, taken_at="2026-09-20T09:30:00Z", content="x")
    assert response.status_code == 404


# --- List ------------------------------------------------------------------------------------


def test_list_notes_newest_first_excluding_deleted_and_other_patients(
    client, create_patient, create_note, patient
):
    other = create_patient(first_name="Other")
    oldest = create_note(patient["id"], taken_at="2025-01-01T09:00:00Z", content="Oldest.")
    newest = create_note(patient["id"], taken_at="2026-01-01T09:00:00Z", content="Newest.")
    deleted = create_note(patient["id"], taken_at="2025-06-01T09:00:00Z", content="Deleted.")
    create_note(other["id"], content="Other patient.")
    client.delete(f"{notes_url(patient['id'])}/{deleted['id']}")

    response = client.get(notes_url(patient["id"]))
    assert response.status_code == 200
    assert [n["id"] for n in response.json()] == [newest["id"], oldest["id"]]


def test_list_notes_empty(client, patient):
    assert client.get(notes_url(patient["id"])).json() == []


# --- Delete (soft) ---------------------------------------------------------------------------


def test_delete_note_hides_it_but_keeps_the_row(client, db, create_note, patient):
    note = create_note(patient["id"])
    url = f"{notes_url(patient['id'])}/{note['id']}"

    assert client.delete(url).status_code == 204
    assert client.get(notes_url(patient["id"])).json() == []
    assert client.delete(url).status_code == 404
    assert db.get(Note, uuid.UUID(note["id"])).deleted_at is not None


def test_delete_note_through_another_patient_is_404(client, create_patient, create_note, patient):
    other = create_patient(first_name="Other")
    note = create_note(patient["id"])

    assert client.delete(f"{notes_url(other['id'])}/{note['id']}").status_code == 404
    assert [n["id"] for n in client.get(notes_url(patient["id"])).json()] == [note["id"]]


def test_delete_unknown_note_is_404(client, patient):
    response = client.delete(f"{notes_url(patient['id'])}/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


def test_delete_note_with_malformed_id_is_422(client, patient):
    assert client.delete(f"{notes_url(patient['id'])}/not-a-uuid").status_code == 422


# --- Deleted patient -------------------------------------------------------------------------


def test_deleted_patients_notes_and_summary_are_404(client, create_note, patient):
    note = create_note(patient["id"])
    client.delete(f"/patients/{patient['id']}")

    assert client.get(notes_url(patient["id"])).status_code == 404
    response = post_note(client, patient["id"], taken_at=note["taken_at"], content="x")
    assert response.status_code == 404
    assert client.delete(f"{notes_url(patient['id'])}/{note['id']}").status_code == 404
    assert client.get(f"/patients/{patient['id']}/summary").status_code == 404


# --- Summary (API) ---------------------------------------------------------------------------


def test_summary_without_notes_still_has_full_profile(client, create_patient):
    patient = create_patient(blood_type="O+", conditions=["Asthma"], allergies=[])
    summary = client.get(f"/patients/{patient['id']}/summary").json()

    assert summary["name"] == "Ana Ruiz"
    assert summary["age"] == patient["age"]
    assert summary["blood_type"] == "O+"
    assert summary["conditions"] == ["Asthma"]
    assert summary["allergies"] == []
    assert "No known allergies." in summary["headline"]
    assert summary["narrative"] == "No clinical notes on file."
    assert (summary["notes_included"], summary["notes_total"]) == (0, 0)
    assert summary["source"] == "template"


def test_summary_uses_latest_ten_live_notes_in_chronological_order(client, create_note, patient):
    notes = [
        create_note(patient["id"], taken_at=f"2026-01-{day:02d}T15:00:00Z", content=f"Visit {day}.")
        for day in range(1, 13)
    ]
    # Deleting the newest leaves 11 live notes: days 2-11 are included, day 1 is omitted.
    client.delete(f"{notes_url(patient['id'])}/{notes[-1]['id']}")

    summary = client.get(f"/patients/{patient['id']}/summary").json()
    narrative = summary["narrative"]

    assert (summary["notes_included"], summary["notes_total"]) == (10, 11)
    assert "latest 10 of 11 notes" in narrative
    assert "1 earlier note not included" in narrative
    assert "Visit 1." not in narrative
    assert "Visit 12." not in narrative
    positions = [narrative.index(f"Visit {day}.") for day in range(2, 12)]
    assert positions == sorted(positions)


# --- Changing the date of birth --------------------------------------------------------------


def test_birth_date_cannot_move_after_an_existing_note(client, create_note, patient):
    create_note(patient["id"], taken_at="2020-06-01T15:00:00Z")

    response = client.put(f"/patients/{patient['id']}", json={"date_of_birth": "2021-01-01"})

    assert error_fields(response) == {"date_of_birth"}
    assert "earliest note, dated 2020-06-01" in response.json()["detail"][0]["msg"]


# 02:00 UTC on Jun 1 is May 31 in New York, the same date note creation would use.
def test_birth_date_check_uses_the_practice_date_of_the_note(client, create_note, patient):
    create_note(patient["id"], taken_at="2020-06-01T02:00:00Z")
    url = f"/patients/{patient['id']}"

    assert error_fields(client.put(url, json={"date_of_birth": "2020-06-01"})) == {"date_of_birth"}
    assert client.put(url, json={"date_of_birth": "2020-05-31"}).status_code == 200


def test_deleted_notes_do_not_block_a_birth_date_correction(client, create_note, patient):
    note = create_note(patient["id"], taken_at="2020-06-01T15:00:00Z")
    client.delete(f"{notes_url(patient['id'])}/{note['id']}")

    response = client.put(f"/patients/{patient['id']}", json={"date_of_birth": "2021-01-01"})

    assert response.status_code == 200
    assert response.json()["date_of_birth"] == "2021-01-01"
