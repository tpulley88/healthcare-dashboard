"""Dependencies shared by the API routes."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient

DbSession = Annotated[Session, Depends(get_db)]


def get_live_patient(patient_id: uuid.UUID, db: DbSession) -> Patient:
    """Load the patient named in the URL, or respond with 404.

    Deleted patients get a 404 too.
    Every route that works on one patient loads it here, so none can forget that check.
    FastAPI creates one session per request, so this shares the route's session.
    """
    query = select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    patient = db.scalar(query)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


LivePatient = Annotated[Patient, Depends(get_live_patient)]
