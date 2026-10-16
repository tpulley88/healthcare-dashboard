import enum
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.dependencies import DbSession, LivePatient
from app.models import Patient, PatientStatus
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


# Escape LIKE wildcards so a search for "100%" matches literally.
def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _order_by(sort: SortField, order: SortOrder) -> list:
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
            # Older patients have earlier birth dates, so age order is the reverse.
            columns = [Patient.date_of_birth.asc() if descending else Patient.date_of_birth.desc()]
        case SortField.LAST_VISIT_DATE:
            columns = [direction(Patient.last_visit_date).nulls_last()]
        case SortField.CREATED_AT:
            columns = [direction(Patient.created_at)]
    # id breaks ties so rows never shift between pages.
    return [*columns, Patient.id]


# Raised as a request validation error so clients get the same 422 shape and field location
# as schema errors. Checked against the merged record on update.
def _check_visit_after_birth(date_of_birth: date, last_visit_date: date | None) -> None:
    if last_visit_date is not None and last_visit_date < date_of_birth:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "last_visit_date"),
                    "msg": "Value error, cannot be before date of birth",
                    "input": last_visit_date.isoformat(),
                }
            ]
        )


@router.get("", response_model=PatientPage)
def list_patients(params: Annotated[PatientListParams, Query()], db: DbSession) -> PatientPage:
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
    return patient


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, db: DbSession) -> Patient:
    _check_visit_after_birth(body.date_of_birth, body.last_visit_date)
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    # Load server-generated values (id, timestamps).
    db.refresh(patient)
    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientRead,
    description=(
        "Partial update: omitted fields remain unchanged, explicit null clears nullable fields, "
        "and supplied arrays replace existing arrays. Name, date of birth, and status cannot be "
        "null. PUT is kept to match the required route; PATCH would be the conventional method."
    ),
)
def update_patient(body: PatientUpdate, patient: LivePatient, db: DbSession) -> Patient:
    changes = body.model_dump(exclude_unset=True)
    _check_visit_after_birth(
        changes.get("date_of_birth", patient.date_of_birth),
        changes.get("last_visit_date", patient.last_visit_date),
    )
    for field, value in changes.items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient: LivePatient, db: DbSession) -> None:
    patient.deleted_at = func.now()
    db.commit()
