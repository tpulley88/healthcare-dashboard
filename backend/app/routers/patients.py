"""Patient routes.

Deletion is soft: a deleted patient keeps its database row and its notes,
but every route treats it as missing and returns 404.
"""

import enum
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app import clock
from app.dependencies import DbSession, LivePatient
from app.errors import field_error
from app.models import Note, Patient, PatientStatus
from app.queries import live_notes
from app.schemas import PatientCreate, PatientPage, PatientRead, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


class SortField(enum.StrEnum):
    NAME = "name"
    AGE = "age"
    LAST_VISIT_DATE = "last_visit_date"
    CREATED_AT = "created_at"


class SortOrder(enum.StrEnum):
    ASC = "asc"
    DESC = "desc"


class PatientListParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    search: str | None = Field(None, max_length=100)
    status: PatientStatus | None = None
    sort: SortField = SortField.NAME
    order: SortOrder = SortOrder.ASC


# Escape LIKE wildcards so that a search for "100%" matches the text literally.
def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _order_by(sort: SortField, order: SortOrder) -> list:
    """Build the ORDER BY columns for the patient list.

    Every sort ends with the patient id.
    Patients with equal sort values then keep a fixed order,
    so none repeat or go missing between pages.
    """
    descending = order is SortOrder.DESC

    def direction(column):
        return column.desc() if descending else column.asc()

    match sort:
        case SortField.NAME:
            columns = [
                direction(func.lower(Patient.last_name)),
                direction(func.lower(Patient.first_name)),
            ]
        case SortField.AGE:
            # Older patients have earlier birth dates, so age order is the reverse of date order.
            columns = [Patient.date_of_birth.asc() if descending else Patient.date_of_birth.desc()]
        case SortField.LAST_VISIT_DATE:
            # Patients with no recorded visit come last in either direction.
            columns = [direction(Patient.last_visit_date).nulls_last()]
        case SortField.CREATED_AT:
            columns = [direction(Patient.created_at)]
    return [*columns, Patient.id]


# On an update, either date may come from the stored record, so this check runs in the route.
def _check_visit_after_birth(date_of_birth: date, last_visit_date: date | None) -> None:
    if last_visit_date is not None and last_visit_date < date_of_birth:
        raise field_error("last_visit_date", "Cannot be before the date of birth", last_visit_date)


def _check_birth_before_notes(db: DbSession, patient: Patient, date_of_birth: date) -> None:
    """Reject a date of birth that falls after any of the patient's notes.

    Note creation enforces the same rule, so the chart stays consistent either way.
    Deleted notes are left out on purpose. They were removed as entered in error,
    and a mistaken note shouldn't block correcting the patient's date of birth.
    """
    earliest = db.scalar(live_notes(patient.id).with_only_columns(func.min(Note.taken_at)))
    if earliest is not None and clock.practice_date(earliest) < date_of_birth:
        first_note = clock.practice_date(earliest)
        message = f"Cannot be after the patient's earliest note, dated {first_note.isoformat()}"
        raise field_error("date_of_birth", message, date_of_birth)


@router.get("", response_model=PatientPage)
def list_patients(params: Annotated[PatientListParams, Query()], db: DbSession) -> PatientPage:
    """List patients one page at a time. Deleted patients are never included.

    `search` matches any part of the full name ("first last"), ignoring case.
    `total` counts every matching patient, not just the ones on this page.
    A page past the end returns an empty list.
    """
    query = select(Patient).where(Patient.deleted_at.is_(None))
    if params.status is not None:
        query = query.where(Patient.status == params.status)
    if params.search and params.search.strip():
        full_name = Patient.first_name + " " + Patient.last_name
        query = query.where(full_name.ilike(_like_pattern(params.search.strip()), escape="\\"))

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    patients = db.scalars(
        query.order_by(*_order_by(params.sort, params.order))
        .limit(params.page_size)
        .offset((params.page - 1) * params.page_size)
    ).all()
    return PatientPage(
        items=[PatientRead.model_validate(p) for p in patients],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient: LivePatient) -> Patient:
    """Get one patient. A deleted patient returns 404."""
    return patient


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, db: DbSession) -> Patient:
    """Create a patient. If `status` isn't sent, the patient starts as active."""
    _check_visit_after_birth(body.date_of_birth, body.last_visit_date)
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    # Load the values the database generated: the id and the timestamps.
    db.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientRead)
def update_patient(body: PatientUpdate, patient: LivePatient, db: DbSession) -> Patient:
    """Update a patient. Only the fields you send are changed.

    - A field you leave out keeps its current value.
    - A field you send as null is cleared. Name, date of birth, and status can't be cleared.
    - A list you send, such as allergies, replaces the stored list.
    - An empty body changes nothing and returns the patient as stored.

    The route uses PUT to match the specified API.
    PATCH is the more common method for partial updates.
    """
    # exclude_unset keeps only the fields the client sent, so a sent null is kept
    # and an omitted field is skipped.
    changes = body.model_dump(exclude_unset=True)
    _check_visit_after_birth(
        changes.get("date_of_birth", patient.date_of_birth),
        changes.get("last_visit_date", patient.last_visit_date),
    )
    if "date_of_birth" in changes:
        _check_birth_before_notes(db, patient, changes["date_of_birth"])
    for field, value in changes.items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient: LivePatient, db: DbSession) -> None:
    """Delete a patient.

    This is a soft delete. The patient and their notes stay in the database,
    but every endpoint then returns 404 for this patient, including a second delete.
    """
    patient.deleted_at = func.now()
    db.commit()
