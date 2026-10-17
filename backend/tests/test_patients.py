import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Note, Patient
from app.schemas import calculate_age, earliest_birth_date
from tests.helpers import MISSING_ID, error_fields

# --- Create ----------------------------------------------------------------------------------


def test_create_normalizes_input(create_patient):
    patient = create_patient(
        first_name="  Ana ",
        phone="+1 617.555.0142",
        state="ma",
        postal_code="02118",
        allergies=["Penicillin", "penicillin", " Latex "],
    )
    assert patient["first_name"] == "Ana"
    assert patient["phone"] == "(617) 555-0142"
    assert patient["state"] == "MA"
    assert patient["postal_code"] == "02118"
    assert patient["allergies"] == ["Penicillin", "Latex"]
    assert patient["status"] == "active"
    assert {"id", "age", "created_at", "updated_at"} <= patient.keys()
    assert "deleted_at" not in patient


def test_create_keeps_not_recorded_distinct_from_none_known(create_patient):
    patient = create_patient(allergies=None, conditions=[])
    assert patient["allergies"] is None
    assert patient["conditions"] == []


def test_create_requires_name_and_birth_date(client):
    response = client.post("/patients", json={})
    assert error_fields(response) == {"first_name", "last_name", "date_of_birth"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", "   "),
        ("date_of_birth", (date.today() + timedelta(days=1)).isoformat()),
        ("date_of_birth", "1850-01-01"),
        ("date_of_birth", (earliest_birth_date(date.today()) - timedelta(days=1)).isoformat()),
        ("phone", "555-0142"),
        ("email", "not-an-email"),
        ("state", "ZZ"),
        ("postal_code", "2118"),
        ("blood_type", "C+"),
        ("status", "discharged"),
        ("allergies", ["Penicillin", ""]),
        ("last_visit_date", (date.today() + timedelta(days=1)).isoformat()),
        ("id", MISSING_ID),
        ("deleted_at", None),
    ],
)
def test_create_rejects_invalid_field(client, field, value):
    body = {"first_name": "Ana", "last_name": "Ruiz", "date_of_birth": "1958-03-02", field: value}
    assert error_fields(client.post("/patients", json=body)) == {field}


@pytest.mark.parametrize(
    ("raw", "stored"),
    [
        ("6175550123", "(617) 555-0123"),
        ("617-555-0123", "(617) 555-0123"),
        ("617.555.0123", "(617) 555-0123"),
        ("617 555 0123", "(617) 555-0123"),
        ("(617) 555-0123", "(617) 555-0123"),
        ("(617)555-0123", "(617) 555-0123"),
        ("+1 617 555 0123", "(617) 555-0123"),
        ("1-617-555-0123", "(617) 555-0123"),
        (" 617-555-0123 ", "(617) 555-0123"),
    ],
)
def test_create_accepts_us_phone_formats(create_patient, raw, stored):
    assert create_patient(phone=raw)["phone"] == stored


@pytest.mark.parametrize(
    "raw",
    [
        "garbage6175550123",
        "6175550123 ext",
        "617-555-0123 x12",
        "617-555-0123 ext. 4",
        "(617 555-0123",
        "617) 555-0123",
        "617--555-0123",
        "6175550123a",
        "617-555-01234",
        "+44 20 7946 0958",
        "2-617-555-0123",
    ],
)
def test_create_rejects_malformed_phone(client, raw):
    body = {"first_name": "Ana", "last_name": "Ruiz", "date_of_birth": "1958-03-02", "phone": raw}
    assert error_fields(client.post("/patients", json=body)) == {"phone"}


def test_create_accepts_birth_date_exactly_at_age_limit(create_patient):
    boundary = earliest_birth_date(date.today()).isoformat()
    assert create_patient(date_of_birth=boundary)["date_of_birth"] == boundary


@pytest.mark.parametrize(
    ("today", "earliest"),
    [
        (date(2026, 10, 16), date(1896, 10, 16)),
        (date(2028, 2, 29), date(1898, 2, 28)),
        (date(2030, 2, 28), date(1900, 2, 28)),
    ],
)
def test_earliest_birth_date(today, earliest):
    assert earliest_birth_date(today) == earliest


def test_create_rejects_visit_before_birth(client):
    body = {
        "first_name": "Ana",
        "last_name": "Ruiz",
        "date_of_birth": "1958-03-02",
        "last_visit_date": "1950-01-01",
    }
    assert error_fields(client.post("/patients", json=body)) == {"last_visit_date"}


# --- Read ------------------------------------------------------------------------------------


def test_get_patient(client, create_patient):
    created = create_patient()
    response = client.get(f"/patients/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_patient_is_404(client):
    response = client.get(f"/patients/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found"}


def test_get_malformed_id_is_422(client):
    assert client.get("/patients/not-a-uuid").status_code == 422


@pytest.mark.parametrize(
    ("born", "today", "age"),
    [
        (date(1958, 3, 2), date(2026, 3, 1), 67),
        (date(1958, 3, 2), date(2026, 3, 2), 68),
        (date(2000, 2, 29), date(2026, 2, 28), 25),
        (date(2000, 2, 29), date(2026, 3, 1), 26),
    ],
)
def test_calculate_age(born, today, age):
    assert calculate_age(born, today) == age


# --- Update (partial) ------------------------------------------------------------------------


def update(client, patient_id, body):
    return client.put(f"/patients/{patient_id}", json=body)


def test_update_changes_only_supplied_fields(client, create_patient):
    created = create_patient(phone="6175550142", allergies=["Penicillin"], status="inactive")
    response = update(client, created["id"], {"phone": "617-555-0199"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["phone"] == "(617) 555-0199"
    unchanged = {k: v for k, v in created.items() if k not in {"phone", "updated_at"}}
    assert {k: updated[k] for k in unchanged} == unchanged


def test_update_null_clears_and_empty_list_means_none_known(client, create_patient):
    created = create_patient(phone="6175550142", allergies=["Penicillin"], conditions=["Asthma"])
    updated = update(client, created["id"], {"phone": None, "allergies": None, "conditions": []})
    assert updated.json()["phone"] is None
    assert updated.json()["allergies"] is None
    assert updated.json()["conditions"] == []


def test_update_supplied_list_replaces_stored_list(client, create_patient):
    created = create_patient(allergies=["Penicillin", "Latex"])
    updated = update(client, created["id"], {"allergies": ["Sulfa"]})
    assert updated.json()["allergies"] == ["Sulfa"]


@pytest.mark.parametrize("field", ["first_name", "last_name", "date_of_birth", "status"])
def test_update_rejects_null_for_required_field(client, create_patient, field):
    created = create_patient()
    assert error_fields(update(client, created["id"], {field: None})) == {field}


def test_update_checks_visit_date_against_stored_birth_date(client, create_patient):
    created = create_patient(date_of_birth="1958-03-02")
    response = update(client, created["id"], {"last_visit_date": "1950-01-01"})
    assert error_fields(response) == {"last_visit_date"}


def test_update_checks_birth_date_against_stored_visit_date(client, create_patient):
    created = create_patient(date_of_birth="1958-03-02", last_visit_date="2026-01-15")
    response = update(client, created["id"], {"date_of_birth": "2026-02-01"})
    assert error_fields(response) == {"last_visit_date"}


def test_update_with_empty_body_is_a_no_op(client, create_patient):
    created = create_patient()
    response = update(client, created["id"], {})
    assert response.status_code == 200
    assert response.json() == created


def test_update_rejects_unknown_field(client, create_patient):
    created = create_patient()
    assert error_fields(update(client, created["id"], {"deleted_at": None})) == {"deleted_at"}


def test_update_unknown_patient_is_404(client):
    assert update(client, MISSING_ID, {"phone": "6175550142"}).status_code == 404


# --- Delete (soft) ---------------------------------------------------------------------------


def test_delete_hides_patient_from_every_route(client, create_patient):
    kept = create_patient(last_name="Kept")
    deleted = create_patient(last_name="Deleted")

    assert client.delete(f"/patients/{deleted['id']}").status_code == 204

    assert client.get(f"/patients/{deleted['id']}").status_code == 404
    assert update(client, deleted["id"], {}).status_code == 404
    assert client.delete(f"/patients/{deleted['id']}").status_code == 404
    listing = client.get("/patients").json()
    assert [p["id"] for p in listing["items"]] == [kept["id"]]
    assert listing["total"] == 1


def test_delete_retains_patient_row_and_notes(client, db, create_patient):
    patient_id = uuid.UUID(create_patient()["id"])
    db.add(Note(patient_id=patient_id, taken_at=datetime.now().astimezone(), content="Seen"))
    db.commit()

    client.delete(f"/patients/{patient_id}")

    patient = db.get(Patient, patient_id)
    assert patient.deleted_at is not None
    assert db.scalar(select(Note.content).where(Note.patient_id == patient.id)) == "Seen"


def test_database_rejects_physical_delete(db, create_patient):
    created = create_patient()
    with pytest.raises(IntegrityError, match="soft-deleted"):
        db.execute(text("DELETE FROM patients WHERE id = :id"), {"id": created["id"]})


# --- List ------------------------------------------------------------------------------------


def names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [f"{p['first_name']} {p['last_name']}" for p in response.json()["items"]]


def test_list_paginates_with_total(client, create_patient):
    for i in range(5):
        create_patient(last_name=f"Patient{i}")

    page = client.get("/patients", params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 5
    assert (page["page"], page["page_size"]) == (2, 2)
    assert [p["last_name"] for p in page["items"]] == ["Patient2", "Patient3"]

    past_end = client.get("/patients", params={"page": 4, "page_size": 2}).json()
    assert past_end["items"] == []
    assert past_end["total"] == 5


def test_list_pages_are_stable_when_sort_values_tie(client, create_patient):
    created = {create_patient()["id"] for _ in range(5)}
    seen = []
    for page in (1, 2, 3):
        response = client.get("/patients", params={"page": page, "page_size": 2})
        seen += [p["id"] for p in response.json()["items"]]
    assert sorted(seen) == sorted(created)


def test_list_search_matches_full_name_case_insensitively(client, create_patient):
    create_patient(first_name="Ana", last_name="Ruiz")
    create_patient(first_name="Marcus", last_name="Chen")

    assert names(client.get("/patients", params={"search": "  ana ruiz "})) == ["Ana Ruiz"]
    assert names(client.get("/patients", params={"search": "CHE"})) == ["Marcus Chen"]


@pytest.mark.parametrize("term", ["%", "_", "\\"])
def test_list_search_treats_wildcards_literally(client, create_patient, term):
    create_patient(first_name="Ana", last_name="Ruiz")
    assert names(client.get("/patients", params={"search": term})) == []


def test_list_filters_by_status(client, create_patient):
    create_patient(first_name="Active")
    create_patient(first_name="Inactive", status="inactive")
    assert names(client.get("/patients", params={"status": "inactive"})) == ["Inactive Ruiz"]


def test_list_sorts_by_name_ignoring_case(client, create_patient):
    for last in ["chen", "Abernathy", "Brooks"]:
        create_patient(first_name="Pat", last_name=last)
    response = client.get("/patients", params={"sort": "name", "order": "desc"})
    assert names(response) == ["Pat chen", "Pat Brooks", "Pat Abernathy"]


def test_list_sorts_by_age(client, create_patient):
    create_patient(first_name="Middle", date_of_birth="1970-01-01")
    create_patient(first_name="Oldest", date_of_birth="1940-01-01")
    create_patient(first_name="Youngest", date_of_birth="2000-01-01")
    response = client.get("/patients", params={"sort": "age", "order": "desc"})
    assert names(response) == ["Oldest Ruiz", "Middle Ruiz", "Youngest Ruiz"]


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_list_sorts_missing_last_visit_last(client, create_patient, order):
    create_patient(first_name="Never")
    create_patient(first_name="Early", last_visit_date="2025-01-01")
    create_patient(first_name="Late", last_visit_date="2026-01-01")
    response = client.get("/patients", params={"sort": "last_visit_date", "order": order})
    visited = ["Early Ruiz", "Late Ruiz"] if order == "asc" else ["Late Ruiz", "Early Ruiz"]
    assert names(response) == [*visited, "Never Ruiz"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
        {"sort": "ssn"},
        {"order": "sideways"},
        {"status": "discharged"},
        {"search": "x" * 101},
    ],
)
def test_list_rejects_invalid_query_params(client, params):
    assert client.get("/patients", params=params).status_code == 422
