"""Template-based patient summary.

The narrative is a dated timeline built from the opening of each recent note.
It puts notes in order and connects them in time, but it doesn't interpret them clinically.
Nothing here reads the database or the clock, so the same inputs always give the same summary.
"""

import re
from collections.abc import Sequence
from datetime import date
from zoneinfo import ZoneInfo

from app.models import Note, Patient, PatientStatus
from app.schemas import PatientSummary, calculate_age

RECENT_NOTE_LIMIT = 10
# A first sentence shorter than this reads like a heading, such as "BP follow-up.",
# so the next sentence is included too.
HEADING_LENGTH = 40
EXCERPT_LIMIT = 160
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


def _format_date(value: date) -> str:
    return f"{value:%b} {value.day}, {value.year}"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


# None means "not recorded" and an empty list means "none known", so each reads differently.
def _clinical_list(items: list[str] | None, label: str, none_known: str) -> str:
    if items is None:
        return f"{label} not recorded."
    if not items:
        return none_known
    return f"{label}: {', '.join(items)}."


def _headline(patient: Patient, today: date) -> str:
    name = f"{patient.first_name} {patient.last_name}"
    if patient.status is PatientStatus.DECEASED:
        # No date of death is stored, so an age here would keep counting up after death.
        identity = (
            f"{name} (deceased; born {_format_date(patient.date_of_birth)}; "
            "date of death not recorded)."
        )
    else:
        age = calculate_age(patient.date_of_birth, today)
        inactive = ", currently inactive" if patient.status is PatientStatus.INACTIVE else ""
        identity = f"{name} is a {age}-year-old patient{inactive}."
    blood_type = (
        f"Blood type {patient.blood_type}." if patient.blood_type else "Blood type not recorded."
    )
    return " ".join(
        [
            identity,
            blood_type,
            _clinical_list(patient.conditions, "Conditions", "No known chronic conditions."),
            _clinical_list(patient.allergies, "Allergies", "No known allergies."),
        ]
    )


def _excerpt(content: str) -> str:
    """The opening of a note: its first sentence, plus the second if the first is a heading.

    Line breaks become spaces. Long excerpts are cut at a word boundary and end with "…".
    """
    sentences = _SENTENCE_BREAK.split(" ".join(content.split()))
    excerpt = sentences[0]
    if len(excerpt) < HEADING_LENGTH and len(sentences) > 1:
        excerpt = f"{excerpt} {sentences[1]}"
    if len(excerpt) > EXCERPT_LIMIT:
        excerpt = excerpt[:EXCERPT_LIMIT].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return excerpt


def _gap(days: int) -> str:
    if days == 0:
        return "Later the same day"
    if days < 14:
        return f"{_plural(days, 'day')} later"
    if days < 60:
        return f"{days // 7} weeks later"
    if days < 730:
        return f"{days // 30} months later"
    return f"{days // 365} years later"


def _timeline(dated_notes: list[tuple[date, Note]]) -> list[str]:
    entries = []
    previous: date | None = None
    for index, (day, note) in enumerate(dated_notes):
        when = _format_date(day)
        if previous is None:
            lead = f"On {when}"
        elif index == len(dated_notes) - 1:
            lead = f"Most recently ({when})"
        else:
            lead = f"{_gap((day - previous).days)} ({when})"
        entries.append(f"{lead}: {_excerpt(note.content)}")
        previous = day
    return entries


def _narrative(recent_notes: Sequence[Note], notes_total: int, tz: ZoneInfo) -> str:
    if not recent_notes:
        return "No clinical notes on file."
    dated = [(note.taken_at.astimezone(tz).date(), note) for note in recent_notes]
    first, last = _format_date(dated[0][0]), _format_date(dated[-1][0])
    span = f"on {first}" if first == last else f"from {first} to {last}"
    included = len(recent_notes)
    if included == notes_total:
        coverage = f"Recent-note summary of {_plural(included, 'note')} {span}."
    else:
        omitted = notes_total - included
        coverage = (
            f"Recent-note summary of the latest {included} of {notes_total} notes, {span}; "
            f"{_plural(omitted, 'earlier note')} not included."
        )
    return " ".join([coverage, "Not a complete clinical history.", *_timeline(dated)])


def build_summary(
    patient: Patient,
    recent_notes: Sequence[Note],
    notes_total: int,
    today: date,
    tz: ZoneInfo,
) -> PatientSummary:
    """Build the summary for one patient.

    `recent_notes` must be the patient's latest notes that haven't been deleted, oldest first.
    `notes_total` must count all of the patient's notes that haven't been deleted.
    Both come from the same set of notes, so the number reported as left out is accurate.
    `today` and `tz` are passed in rather than read from the clock, which keeps tests predictable.
    """
    return PatientSummary(
        patient_id=patient.id,
        name=f"{patient.first_name} {patient.last_name}",
        age=calculate_age(patient.date_of_birth, today),
        date_of_birth=patient.date_of_birth,
        blood_type=patient.blood_type,
        status=patient.status,
        conditions=patient.conditions,
        allergies=patient.allergies,
        headline=_headline(patient, today),
        narrative=_narrative(recent_notes, notes_total, tz),
        notes_included=len(recent_notes),
        notes_total=notes_total,
    )
