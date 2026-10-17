"""Clinical note and summary routes.

Notes are reached only through a patient that hasn't been deleted,
so a deleted patient's notes and summary return 404.
Notes can't be edited. To correct one, delete it and add a new note.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app import clock
from app.config import settings
from app.dependencies import DbSession, LivePatient
from app.errors import field_error
from app.models import Note
from app.queries import live_notes
from app.schemas import NoteCreate, NoteRead, PatientSummary
from app.summary import RECENT_NOTE_LIMIT, build_summary

router = APIRouter(prefix="/patients/{patient_id}", tags=["notes"])


@router.get("/notes", response_model=list[NoteRead])
def list_notes(patient: LivePatient, db: DbSession) -> list[Note]:
    """List a patient's notes, newest first. Deleted notes are left out."""
    query = live_notes(patient.id).order_by(Note.taken_at.desc(), Note.id.desc())
    return list(db.scalars(query))


@router.post("/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(body: NoteCreate, patient: LivePatient, db: DbSession) -> Note:
    """Add a note to a patient's chart.

    `taken_at` must include a timezone offset.
    It can't be more than 5 minutes in the future, or earlier than the patient's date of birth.
    """
    # Compare calendar dates in the practice's timezone, the same way the chart shows them.
    if clock.practice_date(body.taken_at) < patient.date_of_birth:
        raise field_error("taken_at", "Cannot be before the patient's date of birth", body.taken_at)
    note = Note(patient_id=patient.id, **body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, patient: LivePatient, db: DbSession) -> None:
    """Delete a note, much like marking it "entered in error".

    This is a soft delete. The note stays in the database
    but no longer appears in the notes list or the summary.
    A note that belongs to a different patient returns 404, the same as a missing note.
    """
    note = db.scalar(live_notes(patient.id).where(Note.id == note_id))
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    note.deleted_at = func.now()
    db.commit()


@router.get("/summary", response_model=PatientSummary, tags=["summary"])
def get_summary(patient: LivePatient, db: DbSession) -> PatientSummary:
    """Get a readable summary of a patient's profile and recent notes.

    Name, age, blood type, conditions, and allergies are always included.
    The narrative covers only the 10 most recent notes and says how many earlier notes it left out.
    Each note contributes only its first sentence or two,
    so details later in a note can be missing.
    It isn't a complete clinical history; the full notes are available from the notes endpoint.
    Dates are shown in the practice's timezone.
    """
    query = live_notes(patient.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    latest_first = db.scalars(
        query.order_by(Note.taken_at.desc(), Note.id.desc()).limit(RECENT_NOTE_LIMIT)
    ).all()
    # Reverse the latest notes so the narrative reads from oldest to newest.
    return build_summary(
        patient, latest_first[::-1], total, clock.practice_today(), settings.practice_tz
    )
