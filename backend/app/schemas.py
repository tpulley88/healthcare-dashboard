"""Request and response shapes for the API, with their validation rules.

Address and phone rules assume a US-based practice.
For allergies and conditions, null means "not recorded" and an empty list means "none known".
The two are never treated as the same thing.
"""

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app import clock
from app.models import BloodType, PatientStatus

MAX_AGE_YEARS = 130

# Allows for small clock differences between the client and the server.
FUTURE_NOTE_TOLERANCE = timedelta(minutes=5)

US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)

# The whole value must match, so letters, extensions, and stray characters are rejected
# instead of being silently stripped.
# Format: an optional +1, a 3-digit area code with or without parentheses, then 3 and 4 digits.
US_PHONE = re.compile(r"(?:\+?1[\s.-]?)?(?:\((\d{3})\)|(\d{3}))[\s.-]?(\d{3})[\s.-]?(\d{4})")


def _invalid(message: str) -> PydanticCustomError:
    """A validation error whose message is shown to the client exactly as written."""
    return PydanticCustomError("value_error", message)


def _normalize_phone(value: str) -> str:
    """Accept common US formats and store them all as (617) 555-0123."""
    match = US_PHONE.fullmatch(value.strip())
    if match is None:
        raise _invalid("Must be a 10-digit US phone number, without an extension")
    area = match.group(1) or match.group(2)
    return f"({area}) {match.group(3)}-{match.group(4)}"


def _validate_state(value: str) -> str:
    value = value.upper()
    if value not in US_STATES:
        raise _invalid("Must be a two-letter US state code, or DC")
    return value


def earliest_birth_date(today: date) -> date:
    """The earliest accepted date of birth: exactly MAX_AGE_YEARS before today.

    When today is Feb 29 and that earlier year has no Feb 29, the limit is Feb 28.
    """
    year = today.year - MAX_AGE_YEARS
    try:
        return today.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _validate_birth_date(value: date) -> date:
    today = clock.practice_today()
    if value > today:
        raise _invalid("Cannot be in the future")
    if value < earliest_birth_date(today):
        raise _invalid(f"Cannot be more than {MAX_AGE_YEARS} years ago")
    return value


def _validate_past_date(value: date) -> date:
    if value > clock.practice_today():
        raise _invalid("Cannot be in the future")
    return value


def _not_in_future(value: datetime) -> datetime:
    if value > clock.now() + FUTURE_NOTE_TOLERANCE:
        raise _invalid("Cannot be in the future")
    return value


def _dedupe(items: list[str]) -> list[str]:
    """Remove repeated entries, ignoring case. The first spelling entered is kept."""
    seen: set[str] = set()
    unique = []
    for item in items:
        if item.casefold() not in seen:
            seen.add(item.casefold())
            unique.append(item)
    return unique


def _text(max_length: int) -> type[str]:
    """Text that is trimmed first, then required to be non-empty and at most max_length long."""
    constraints = StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)
    return Annotated[str, constraints]


Name = _text(100)
Street = _text(200)
City = _text(100)
Phone = Annotated[str, AfterValidator(_normalize_phone)]
State = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_validate_state)]
PostalCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{5}(-\d{4})?$")]
BirthDate = Annotated[date, AfterValidator(_validate_birth_date)]
PastDate = Annotated[date, AfterValidator(_validate_past_date)]
ClinicalList = Annotated[list[_text(200)], Field(max_length=50), AfterValidator(_dedupe)]


def calculate_age(born: date, today: date) -> int:
    """Age in completed years. A Feb 29 birthday counts as reached on Mar 1 in other years."""
    had_birthday = (today.month, today.day) >= (born.month, born.day)
    return today.year - born.year - (0 if had_birthday else 1)


class PatientCreate(BaseModel):
    """A new patient. Fields that aren't required may be left out or sent as null."""

    # Unknown fields, such as id, deleted_at, or a misspelled name, are rejected
    # rather than silently ignored.
    model_config = ConfigDict(extra="forbid")

    first_name: Name
    last_name: Name
    date_of_birth: BirthDate
    phone: Phone | None = None
    email: EmailStr | None = None
    street: Street | None = None
    city: City | None = None
    state: State | None = None
    postal_code: PostalCode | None = None
    blood_type: BloodType | None = None
    allergies: ClinicalList | None = None
    conditions: ClinicalList | None = None
    status: PatientStatus = PatientStatus.ACTIVE
    last_visit_date: PastDate | None = None


class PatientUpdate(BaseModel):
    """Changes to a patient. Only the fields sent are applied.

    A field left out keeps its value, null clears it, and a list replaces the stored list.
    First name, last name, date of birth, and status can't be null.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: Name | None = None
    last_name: Name | None = None
    date_of_birth: BirthDate | None = None
    phone: Phone | None = None
    email: EmailStr | None = None
    street: Street | None = None
    city: City | None = None
    state: State | None = None
    postal_code: PostalCode | None = None
    blood_type: BloodType | None = None
    allergies: ClinicalList | None = None
    conditions: ClinicalList | None = None
    status: PatientStatus | None = None
    last_visit_date: PastDate | None = None

    # Pydantic doesn't validate default values, so this only runs when a client sends null.
    # Leaving these fields out is still allowed.
    @field_validator("first_name", "last_name", "date_of_birth", "status")
    @classmethod
    def _not_null(cls, value: object) -> object:
        if value is None:
            raise _invalid("Cannot be null")
        return value


class PatientRead(BaseModel):
    """A patient as returned by the API.

    Age is calculated on every read, from the date of birth and today's date at the practice.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str | None
    email: str | None
    street: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    blood_type: BloodType | None
    allergies: list[str] | None
    conditions: list[str] | None
    status: PatientStatus
    last_visit_date: date | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def age(self) -> int:
        return calculate_age(self.date_of_birth, clock.practice_today())


class PatientPage(BaseModel):
    """One page of patients. `total` counts every matching patient across all pages."""

    items: list[PatientRead]
    total: int
    page: int
    page_size: int


class NoteCreate(BaseModel):
    """A new clinical note.

    `taken_at` is when the care happened. It must include a timezone offset,
    for example 2026-09-20T09:30:00-04:00, because a time without one is ambiguous.
    `content` is trimmed before its length is checked, so a note of only spaces is rejected.
    Line breaks inside the note are kept.
    """

    model_config = ConfigDict(extra="forbid")

    taken_at: Annotated[AwareDatetime, AfterValidator(_not_in_future)]
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)
    ]


class NoteRead(BaseModel):
    """A clinical note. `taken_at` is when the care happened; `created_at` is when it was saved."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    taken_at: datetime
    content: str
    created_at: datetime


class PatientSummary(BaseModel):
    """A readable summary of a patient's profile and recent notes.

    The profile fields are always present, even when the patient has no notes.
    The narrative covers only the most recent notes. `notes_included` and `notes_total`
    show how many it covers, because it isn't a complete clinical history.
    `source` is "template" today. It leaves room for an optional LLM-generated narrative later.
    """

    patient_id: uuid.UUID
    name: str
    age: int
    date_of_birth: date
    blood_type: BloodType | None
    status: PatientStatus
    conditions: list[str] | None
    allergies: list[str] | None
    headline: str
    narrative: str
    notes_included: int
    notes_total: int
    source: Literal["template"] = "template"
