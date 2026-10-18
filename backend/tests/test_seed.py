from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Patient
from app.schemas import PatientCreate, calculate_age
from app.seed import ANCHOR_DATE, PATIENT_COUNT, seed

PATIENT_FIELDS = set(PatientCreate.model_fields)


def seeded(db) -> list[Patient]:
    assert seed(db) == PATIENT_COUNT
    return list(db.scalars(select(Patient).options(selectinload(Patient.notes))))


def test_seed_runs_once(db):
    seeded(db)
    assert seed(db) == 0


def test_seeded_patients_pass_api_validation(db):
    for patient in seeded(db):
        PatientCreate.model_validate({field: getattr(patient, field) for field in PATIENT_FIELDS})


def test_only_patients_never_seen_have_unknown_lists(db):
    for patient in seeded(db):
        never_seen = not patient.notes
        assert (patient.conditions is None) == never_seen
        assert (patient.allergies is None) == never_seen


def test_no_patient_has_two_notes_from_the_same_template(db):
    for patient in seeded(db):
        # Templates differ in their opening words; filled-in numbers come later.
        openings = [note.content[:25] for note in patient.notes]
        assert len(openings) == len(set(openings))


def test_older_patients_more_often_have_conditions(db):
    def share_with_none_known(patients: list[Patient]) -> float:
        seen = [p for p in patients if p.conditions is not None]
        return sum(1 for p in seen if not p.conditions) / len(seen)

    patients = seeded(db)
    age = {p.id: calculate_age(p.date_of_birth, ANCHOR_DATE) for p in patients}
    young = [p for p in patients if age[p.id] < 40]
    older = [p for p in patients if age[p.id] >= 65]
    assert share_with_none_known(older) < share_with_none_known(young)


def test_seed_dates_stay_before_the_anchor_date(db):
    for patient in seeded(db):
        assert patient.date_of_birth < ANCHOR_DATE
        assert all(note.taken_at.date() < ANCHOR_DATE for note in patient.notes)
        if patient.last_visit_date is not None:
            assert patient.last_visit_date < ANCHOR_DATE
