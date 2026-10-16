import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient

DbSession = Annotated[Session, Depends(get_db)]


# The one place patient-scoped routes load a patient, so none can forget the deleted check.
# FastAPI caches get_db per request, so this shares the route's session.
def get_live_patient(patient_id: uuid.UUID, db: DbSession) -> Patient:
    query = select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    patient = db.scalar(query)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient


LivePatient = Annotated[Patient, Depends(get_live_patient)]
