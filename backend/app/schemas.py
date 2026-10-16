import re
import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)

from app.models import BloodType, PatientStatus

MAX_AGE_YEARS = 130

# US-only while the practice is US-based: 50 states plus DC.
US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)


# Accepts common US formats and stores one canonical form. US numbers only while the
# practice is US-based.
# Matches the whole value, so letters, extensions and stray characters are rejected rather
# than stripped: optional +1, area code with or without parentheses, then 3 and 4 digits.
US_PHONE = re.compile(r"(?:\+?1[\s.-]?)?(?:\((\d{3})\)|(\d{3}))[\s.-]?(\d{3})[\s.-]?(\d{4})")


def _normalize_phone(value: str) -> str:
    match = US_PHONE.fullmatch(value.strip())
    if match is None:
        raise ValueError("must be a 10-digit US phone number, without an extension")
    area = match.group(1) or match.group(2)
    return f"({area}) {match.group(3)}-{match.group(4)}"


def _validate_state(value: str) -> str:
    value = value.upper()
    if value not in US_STATES:
        raise ValueError("must be a US state or DC two-letter code")
    return value


# Exact calendar boundary: born on this date or later. On Feb 29 in a year whose
# counterpart isn't a leap year, the boundary falls on Feb 28.
def earliest_birth_date(today: date) -> date:
    year = today.year - MAX_AGE_YEARS
    try:
        return today.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _validate_birth_date(value: date) -> date:
    today = date.today()
    if value > today:
        raise ValueError("cannot be in the future")
    if value < earliest_birth_date(today):
        raise ValueError(f"cannot be more than {MAX_AGE_YEARS} years ago")
    return value


def _validate_past_date(value: date) -> date:
    if value > date.today():
        raise ValueError("cannot be in the future")
    return value


# Case-insensitive de-duplication that keeps the first spelling entered.
def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in items:
        if item.casefold() not in seen:
            seen.add(item.casefold())
            unique.append(item)
    return unique


def _text(max_length: int) -> type[str]:
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
# None means "not recorded" and [] means "none known"; the two are never merged.
ClinicalList = Annotated[list[_text(200)], Field(max_length=50), AfterValidator(_dedupe)]


# A Feb 29 birthday counts as passed on Mar 1 in non-leap years.
def calculate_age(born: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (born.month, born.day)
    return today.year - born.year - (0 if had_birthday else 1)


class PatientCreate(BaseModel):
    # Unknown fields (id, deleted_at, typos) are rejected rather than silently ignored.
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


# Partial update: omitted fields are unchanged, null clears a nullable field, and a supplied
# list replaces the stored list. The route uses model_dump(exclude_unset=True) to tell
# omitted from null.
class PatientUpdate(BaseModel):
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

    # Defaults aren't validated, so this only fires when a client sends an explicit null.
    @field_validator("first_name", "last_name", "date_of_birth", "status")
    @classmethod
    def _not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class PatientRead(BaseModel):
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

    # Derived on every read so it never goes stale.
    @computed_field
    @property
    def age(self) -> int:
        return calculate_age(self.date_of_birth, date.today())


class PatientPage(BaseModel):
    items: list[PatientRead]
    total: int
    page: int
    page_size: int
