from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError


def field_error(field: str, message: str, value: object) -> RequestValidationError:
    """Build a 422 error that points at one field of the request body.

    Use this for rules that depend on stored data, such as comparing a date with the
    patient's saved date of birth. Schemas only see the request, so those checks run in routes.
    The error has the same shape as schema validation errors, so clients handle both the same way.
    """
    error = {"type": "value_error", "loc": ("body", field), "msg": message, "input": str(value)}
    return RequestValidationError([error])


STALE_PATIENT_MESSAGE = (
    "This patient was changed by someone else. Reload it and review the changes before saving."
)


def stale_patient_error() -> HTTPException:
    """Build the 412 returned when a save is based on an outdated copy of the patient."""
    return HTTPException(status.HTTP_412_PRECONDITION_FAILED, STALE_PATIENT_MESSAGE)
