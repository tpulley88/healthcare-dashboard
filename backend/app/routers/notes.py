"""Clinical note and summary routes.

Notes are reached only through a patient that hasn't been deleted,
so a deleted patient's notes and summary return 404.
Notes can't be edited. To correct one, delete it and add a new note.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app import clock
from app.config import settings
from app.dependencies import DbSession, LivePatient
from app.errors import field_error
from app.generated_summary import (
    NarrativeWriter,
    ProviderError,
    build_prompt,
    check_action_items,
    get_narrative_writer,
    is_shortened,
    remembered_narrative,
)
from app.models import Note, Patient, PatientStatus
from app.queries import live_notes
from app.schemas import ActionItemRead, NoteCreate, NoteRead, PatientSummary
from app.summary import RECENT_NOTE_LIMIT, build_summary

# "auto" uses a generated narrative when one is available; "template" always uses the built-in.
SummarySource = Literal["auto", "template"]

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
def get_summary(
    patient: LivePatient,
    db: DbSession,
    write: Annotated[NarrativeWriter | None, Depends(get_narrative_writer)],
    source: Annotated[SummarySource, Query()] = "auto",
) -> PatientSummary:
    """Get a readable summary of a patient's profile and recent notes.

    Name, age, blood type, conditions, and allergies always come from the database.
    The narrative covers the 10 most recent notes. The response says how many notes it includes
    out of the total, and the dates of the first and last, so clients can show that.
    It isn't a complete clinical history; the full notes are available from the notes endpoint.
    Dates are shown in the practice's timezone.

    With `source=auto` (the default) and an OpenAI API key configured, a language model writes
    the narrative from the note text (`source` "llm"): a short summary of where things stand,
    combining the notes rather than recounting each visit. `action_items` lists follow-ups the
    notes planned that no later note shows as done; the model may not add its own. Each has the
    date of the note that planned it and, when the note gives one, a due date; `overdue` is
    worked out here from today's date, not by the model, and is never set for a deceased
    patient. Items due soonest come first, then those with no due date.
    Each note is sent up to its first 4,000 characters; `notes_shortened` counts the notes that
    were cut, so anything after that point, such as a long note's Assessment and Plan, may be
    missing from the narrative.
    The patient's name, date of birth, and contact details aren't sent.
    The first request for a given set of notes can take several seconds; repeats are answered
    from memory until the notes or profile change.
    A model can misread or leave out details, so check the narrative against the notes.

    Otherwise the narrative is built in (`source` "template"): one dated line per note, newest
    first, using each SOAP note's Assessment and Plan, or the opening of other notes.
    `fallback_reason` says why the built-in narrative was used when a generated one was wanted.
    `source=template` asks for the built-in narrative without contacting the model.
    """
    notes, total = _recent_notes(patient, db)
    today, tz = clock.practice_today(), settings.practice_tz
    summary = build_summary(patient, notes, total, today, tz)
    if source == "template" or not notes:
        return summary
    if write is None:
        return summary.model_copy(update={"fallback_reason": "not_configured"})
    try:
        generated = remembered_narrative(build_prompt(patient, notes, total, today, tz), write)
        check_action_items(generated.action_items, {clock.practice_date(n.taken_at) for n in notes})
    except ProviderError:
        return summary.model_copy(update={"fallback_reason": "provider_error"})
    shortened = sum(is_shortened(note) for note in notes)
    items = sorted(
        generated.action_items, key=lambda item: (item.due_on is None, item.due_on or item.noted_on)
    )
    return summary.model_copy(
        update={
            "narrative": generated.summary,
            "action_items": [
                ActionItemRead(
                    action=item.action,
                    noted_on=item.noted_on,
                    due_on=item.due_on,
                    # Nothing is overdue for a patient who has died.
                    overdue=patient.status is not PatientStatus.DECEASED
                    and item.due_on is not None
                    and item.due_on < today,
                )
                for item in items
            ],
            "source": "llm",
            "notes_shortened": shortened,
        }
    )


def _recent_notes(patient: Patient, db: DbSession) -> tuple[list[Note], int]:
    """The latest notes, oldest first, and the count of all notes. Deleted notes are left out."""
    query = live_notes(patient.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    latest_first = db.scalars(
        query.order_by(Note.taken_at.desc(), Note.id.desc()).limit(RECENT_NOTE_LIMIT)
    ).all()
    # Oldest first, so the dates read forward for the model and gaps between notes can be measured.
    return list(latest_first[::-1]), total
