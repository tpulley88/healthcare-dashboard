"""Database models.

Patients and notes are never physically deleted. Each has a deleted_at timestamp instead,
and a database trigger (migration 0002) rejects any DELETE statement.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Predictable constraint names, so future migrations can refer to them by name.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Common outpatient EHR statuses. "Discharged" is left out because it's an inpatient term.
class PatientStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DECEASED = "deceased"


class BloodType(enum.StrEnum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


# Stored as text with a CHECK constraint, because a native Postgres ENUM is awkward to change.
# values_callable stores each value, such as "A+", rather than the Python name, such as "A_POS".
def _string_enum(enum_cls: type[enum.Enum], name: str, length: int) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class Patient(Base):
    """A patient record. Age isn't stored; it's calculated from the date of birth when read."""

    __tablename__ = "patients"

    # UUIDs can't be guessed, don't reveal how many patients exist,
    # and can be created by other systems without clashing.
    # Postgres generates them, so rows inserted with plain SQL get one too.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)

    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))

    # US address. The postal code is text so leading zeros survive, as in 02118.
    street: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(2))
    postal_code: Mapped[str | None] = mapped_column(String(10))

    # For allergies and conditions, NULL means "unknown" and an empty list means "none known".
    blood_type: Mapped[BloodType | None] = mapped_column(_string_enum(BloodType, "blood_type", 3))
    allergies: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # This default is applied by SQLAlchemy only. Plain SQL inserts must supply a status.
    status: Mapped[PatientStatus] = mapped_column(
        _string_enum(PatientStatus, "status", 20), default=PatientStatus.ACTIVE
    )
    # Stored separately from notes, because not every note is a visit (a phone call, for example).
    last_visit_date: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Updated by SQLAlchemy only. Plain SQL updates leave it unchanged.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Set by DELETE /patients/{id}. Every patient query must leave these rows out.
    # The patient's notes aren't changed; they become unreachable because the patient returns 404.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Goes up by one on every change, so an edit made from an older copy can be detected.
    # SQLAlchemy adds "AND version = <loaded version>" to each UPDATE and raises StaleDataError
    # when no row matches, which means someone else saved in between.
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    __mapper_args__ = {"version_id_col": version}

    # This includes deleted notes, so reads query notes directly with a deleted_at filter.
    # passive_deletes="all" stops SQLAlchemy from changing notes if someone deletes a patient row.
    notes: Mapped[list["Note"]] = relationship(
        back_populates="patient",
        passive_deletes="all",
        order_by="Note.taken_at",
    )


class Note(Base):
    """A clinical note. Notes are never edited; a wrong note is deleted and replaced."""

    __tablename__ = "notes"
    # Supports the main query: one patient's notes in time order.
    __table_args__ = (Index("ix_notes_patient_id_taken_at", "patient_id", "taken_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RESTRICT is a second safeguard behind the no-delete trigger (migration 0002).
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"))
    # When the care happened, as sent by the client. created_at is when the server saved it.
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set when a note is deleted, much like "entered in error": hidden from the chart but kept.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[Patient] = relationship(back_populates="notes")
