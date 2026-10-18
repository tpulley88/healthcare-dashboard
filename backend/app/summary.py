"""Built-in patient summary, used when a generated one isn't available.

The narrative is a dated timeline with one line per recent note.
For SOAP notes the line is the Assessment and Plan, the part clinicians read first.
Other notes contribute their opening sentence or two.
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
# Assessment and Plan together carry more, so they get more room.
ASSESSMENT_PLAN_LIMIT = 240
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
# A SOAP section label at the start of a line, such as "A:" or "Assessment:".
# "A/P" and "Assessment and Plan" are common combined headings.
_SOAP_LABEL = re.compile(
    r"^[ \t]*(assessment and plan|a/p|subjective|objective|assessment|plan|s|o|a|p)[ \t]*:[ \t]*",
    re.IGNORECASE | re.MULTILINE,
)
_SECTION_KEYS = {"subjective": "s", "objective": "o", "assessment": "a", "plan": "p"}


def _format_date(value: date) -> str:
    return f"{value:%b} {value.day}, {value.year}"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


# None means "unknown" and an empty list means "none known", so each reads differently.
def _clinical_list(items: list[str] | None, label: str, none_known: str) -> str:
    if items is None:
        return f"{label} unknown."
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


def _shorten(text: str, limit: int) -> str:
    """Collapse whitespace, then cut at a word boundary with "…" if longer than `limit`."""
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def _soap_sections(content: str) -> dict[str, str]:
    """The note's SOAP sections by key ("s", "o", "a", "p", or "ap"); empty if it has none."""
    matches = list(_SOAP_LABEL.finditer(content))
    if not matches:
        return {}
    sections = {}
    for match, following in zip(matches, matches[1:] + [None], strict=True):
        label = match.group(1).lower()
        key = "ap" if label in ("a/p", "assessment and plan") else _SECTION_KEYS.get(label, label)
        end = following.start() if following else len(content)
        sections[key] = content[match.end() : end].strip()
    return sections


def _excerpt(content: str) -> str:
    """One line for the timeline.

    For a SOAP note, its Assessment and Plan. Otherwise its first sentence,
    plus the second if the first is a heading.
    Line breaks become spaces. Long excerpts are cut at a word boundary and end with "…".
    """
    sections = _soap_sections(content)
    if "ap" in sections or "a" in sections or "p" in sections:
        parts = [sections.get("ap"), sections.get("a")]
        if sections.get("p"):
            parts.append(f"Plan: {sections['p']}")
        return _shorten(" ".join(part for part in parts if part), ASSESSMENT_PLAN_LIMIT)

    sentences = _SENTENCE_BREAK.split(" ".join(content.split()))
    excerpt = sentences[0]
    if len(excerpt) < HEADING_LENGTH and len(sentences) > 1:
        excerpt = f"{excerpt} {sentences[1]}"
    return _shorten(excerpt, EXCERPT_LIMIT)


def _gap(days: int) -> str:
    if days == 0:
        return "later the same day"
    if days < 14:
        return f"{_plural(days, 'day')} later"
    if days < 60:
        return f"{days // 7} weeks later"
    if days < 730:
        return f"{days // 30} months later"
    return f"{days // 365} years later"


# Each entry leads with its date, so the dates line up like a chart.
# The time since the previous note shows gaps in care, such as "11 months later".
def _timeline(dated_notes: list[tuple[date, Note]]) -> list[str]:
    entries = []
    previous: date | None = None
    for index, (day, note) in enumerate(dated_notes):
        details = []
        if previous is not None:
            details.append(_gap((day - previous).days))
            if index == len(dated_notes) - 1:
                details.append("most recent")
        lead = _format_date(day) + (f" ({', '.join(details)})" if details else "")
        entries.append(f"{lead}: {_excerpt(note.content)}")
        previous = day
    return entries


# One line per note, so each visit is easy to pick out.
# Coverage (how many notes, over which dates) is returned as separate fields rather than
# repeated in the text, so clients can label it once in their own words.
def _narrative(dated_notes: list[tuple[date, Note]]) -> str:
    if not dated_notes:
        return "No clinical notes on file."
    return "\n".join(_timeline(dated_notes))


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
    dated = [(note.taken_at.astimezone(tz).date(), note) for note in recent_notes]
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
        narrative=_narrative(dated),
        notes_included=len(recent_notes),
        notes_total=notes_total,
        notes_from=dated[0][0] if dated else None,
        notes_to=dated[-1][0] if dated else None,
    )
