import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.models import BloodType, Note, Patient, PatientStatus
from app.summary import build_summary

TZ = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 17)


# In-memory objects: the summary is a pure function, so no database is needed.
def make_patient(**overrides) -> Patient:
    fields = {
        "id": uuid.uuid4(),
        "first_name": "Ana",
        "last_name": "Ruiz",
        "date_of_birth": date(1958, 3, 2),
        "blood_type": BloodType.O_POS,
        "conditions": ["Hypertension"],
        "allergies": ["Penicillin"],
        "status": PatientStatus.ACTIVE,
    }
    return Patient(**(fields | overrides))


def make_note(taken_at: str, content: str = "Seen.") -> Note:
    return Note(taken_at=datetime.fromisoformat(taken_at), content=content)


def summarize(patient=None, notes=(), total=None):
    notes = list(notes)
    total = len(notes) if total is None else total
    return build_summary(patient or make_patient(), notes, total, TODAY, TZ)


# --- Headline --------------------------------------------------------------------------------


def test_headline_includes_identifiers_and_clinical_lists():
    assert summarize().headline == (
        "Ana Ruiz is a 68-year-old patient. Blood type O+. "
        "Conditions: Hypertension. Allergies: Penicillin."
    )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"allergies": None}, "Allergies unknown."),
        ({"allergies": []}, "No known allergies."),
        ({"conditions": None}, "Conditions unknown."),
        ({"conditions": []}, "No known chronic conditions."),
        ({"blood_type": None}, "Blood type not recorded."),
        ({"status": PatientStatus.INACTIVE}, "68-year-old patient, currently inactive."),
    ],
)
def test_headline_wording(overrides, expected):
    assert expected in summarize(make_patient(**overrides)).headline


def test_deceased_headline_gives_birth_date_instead_of_age():
    headline = summarize(make_patient(status=PatientStatus.DECEASED)).headline
    assert headline.startswith("Ana Ruiz (deceased; born Mar 2, 1958; date of death not recorded).")
    assert "year-old" not in headline


# --- Narrative -------------------------------------------------------------------------------


def test_no_notes():
    summary = summarize()
    assert summary.narrative == "No clinical notes on file."
    assert (summary.notes_included, summary.notes_total) == (0, 0)


def test_single_note():
    narrative = summarize(notes=[make_note("2026-09-20T13:00:00+00:00", "BP follow-up.")]).narrative
    assert narrative == (
        "Recent-note summary of 1 note on Sep 20, 2026. Not a complete clinical history. "
        "On Sep 20, 2026: BP follow-up."
    )


def test_timeline_transitions():
    notes = [
        make_note("2024-01-10T15:00:00+00:00", "First."),
        make_note("2024-01-10T18:00:00+00:00", "Same day."),
        make_note("2024-01-11T15:00:00+00:00", "Next day."),
        make_note("2024-02-08T15:00:00+00:00", "Weeks."),
        make_note("2024-07-08T15:00:00+00:00", "Months."),
        make_note("2026-09-01T15:00:00+00:00", "Years."),
        make_note("2026-09-20T15:00:00+00:00", "Last."),
    ]
    narrative = summarize(notes=notes).narrative
    for phrase in [
        "On Jan 10, 2024: First.",
        "Later the same day (Jan 10, 2024): Same day.",
        "1 day later (Jan 11, 2024): Next day.",
        "4 weeks later (Feb 8, 2024): Weeks.",
        "5 months later (Jul 8, 2024): Months.",
        "2 years later (Sep 1, 2026): Years.",
        "Most recently (Sep 20, 2026): Last.",
    ]:
        assert phrase in narrative


def test_coverage_states_omitted_notes():
    notes = [make_note("2026-01-01T15:00:00+00:00"), make_note("2026-02-01T15:00:00+00:00")]
    narrative = summarize(notes=notes, total=14).narrative
    assert narrative.startswith(
        "Recent-note summary of the latest 2 of 14 notes, from Jan 1, 2026 to Feb 1, 2026; "
        "12 earlier notes not included. Not a complete clinical history."
    )


# 02:00 UTC on Mar 2 is still Mar 1 in New York.
def test_dates_use_practice_timezone():
    narrative = summarize(notes=[make_note("2026-03-02T02:00:00+00:00")]).narrative
    assert "On Mar 1, 2026" in narrative


@pytest.mark.parametrize(
    ("content", "excerpt"),
    [
        # A short heading pulls in the next sentence.
        ("BP follow-up. Home BP 128/82. Tolerating lisinopril.", "BP follow-up. Home BP 128/82."),
        # A full first sentence stands alone.
        (
            "Telephone follow-up on recent lab results. All values normal.",
            "Telephone follow-up on recent lab results.",
        ),
        # Decimals aren't sentence breaks.
        ("A1c 7.2%. Continue metformin.", "A1c 7.2%. Continue metformin."),
        # Line breaks collapse to spaces.
        ("Asthma check.\n\nLungs clear.", "Asthma check. Lungs clear."),
    ],
)
def test_excerpt(content, excerpt):
    narrative = summarize(notes=[make_note("2026-09-20T15:00:00+00:00", content)]).narrative
    assert narrative.endswith(f"On Sep 20, 2026: {excerpt}")


def test_long_excerpt_is_truncated_at_a_word_boundary():
    content = "Word " * 60
    narrative = summarize(notes=[make_note("2026-09-20T15:00:00+00:00", content)]).narrative
    excerpt = narrative.split("On Sep 20, 2026: ")[1]
    assert excerpt.endswith("Word…")
    assert len(excerpt) <= 161


# Age uses the `today` passed in, not a hidden clock.
def test_age_uses_the_given_date():
    patient = make_patient(date_of_birth=date(1958, 10, 18))
    assert build_summary(patient, [], 0, date(2026, 10, 17), TZ).age == 67
    assert build_summary(patient, [], 0, date(2026, 10, 18), TZ).age == 68
