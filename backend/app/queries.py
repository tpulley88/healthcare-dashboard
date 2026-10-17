"""Queries shared by more than one router."""

import uuid

from sqlalchemy import Select, select

from app.models import Note


def live_notes(patient_id: uuid.UUID) -> Select[tuple[Note]]:
    """Start a query for one patient's notes, leaving out deleted ones.

    Every note read starts here. Patient.notes isn't used because it includes deleted notes.
    """
    return select(Note).where(Note.patient_id == patient_id, Note.deleted_at.is_(None))
