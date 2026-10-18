"""Seed the database with synthetic patients when it is empty.

Run as `python -m app.seed`; the container entrypoint does this on every start.
A fixed random seed and anchor date give every environment the same data.
"""

import logging
import random
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import seed_data
from app.db import SessionLocal
from app.models import BloodType, Note, Patient, PatientStatus

# Logs counts only, never patient data.
logger = logging.getLogger(__name__)

# A fixed seed and anchor date make every run produce identical data.
PATIENT_COUNT = 120
RANDOM_SEED = 42
ANCHOR_DATE = date(2026, 10, 1)
TELEPHONE_NOTE = seed_data.GENERAL_NOTES[2]


# SpO2 ranges depend on the note, so COPD and exacerbation notes stay clinically plausible.
def _template_values(rng: random.Random) -> dict[str, object]:
    return {
        "sbp": rng.randint(112, 152),
        "dbp": rng.randint(68, 94),
        "hr": rng.randint(58, 98),
        "spo2": rng.randint(95, 99),
        "spo2_copd": rng.randint(88, 94),
        "spo2_exacerbation": rng.randint(90, 94),
        "a1c": round(rng.uniform(6.2, 8.9), 1),
        "rescue": rng.randint(0, 4),
        "peak_flow": rng.randint(320, 520),
        "fev1_fvc": round(rng.uniform(0.52, 0.68), 2),
        "fev1": rng.randint(48, 79),
        "ldl": rng.randint(72, 168),
        "tsh": round(rng.uniform(0.8, 4.2), 1),
        "cpap_hours": round(rng.uniform(4.5, 7.8), 1),
        "cpap_pct": rng.randint(70, 98),
        "ahi": round(rng.uniform(1.0, 6.0), 1),
        "gad7": rng.randint(3, 12),
        "days": rng.randint(3, 10),
    }


# Rough, illustrative rates for synthetic data, not real prevalence figures.
# Chronic conditions become more common with age, and so does having several.
def _pick_conditions(rng: random.Random, age: int) -> list[str]:
    if age < 40:
        none_known, counts, weights = 0.50, [1, 2], [4, 1]
    elif age < 65:
        none_known, counts, weights = 0.25, [1, 2, 3], [5, 3, 2]
    else:
        none_known, counts, weights = 0.08, [1, 2, 3], [3, 4, 3]
    if rng.random() < none_known:
        return []
    count = rng.choices(counts, weights=weights)[0]
    return rng.sample(list(seed_data.CONDITION_NOTES), count)


# Most patients have no known allergies; about 30% have one, occasionally two.
def _pick_allergies(rng: random.Random) -> list[str]:
    if rng.random() >= 0.30:
        return []
    return rng.sample(seed_data.ALLERGIES, 1 if rng.random() < 0.8 else 2)


# Builds up to `count` notes in time order, plus the date of the most recent in-person visit.
# Each note uses a different template, so no patient has two notes with the same text.
def _build_notes(
    rng: random.Random, conditions: list[str], count: int
) -> tuple[list[Note], date | None]:
    templates = list(seed_data.GENERAL_NOTES)
    for condition in conditions:
        templates.extend(seed_data.CONDITION_NOTES[condition])

    chosen = rng.sample(templates, min(count, len(templates)))
    days_ago = sorted(rng.sample(range(7, 730), len(chosen)), reverse=True)

    notes: list[Note] = []
    last_visit: date | None = None
    for offset, template in zip(days_ago, chosen, strict=True):
        note_date = ANCHOR_DATE - timedelta(days=offset)
        # 13:00 to 21:59 UTC is roughly 9 AM to 6 PM in US Eastern clinic hours.
        taken_at = datetime.combine(
            note_date, time(rng.randint(13, 21), rng.choice([0, 15, 30, 45])), tzinfo=UTC
        )
        notes.append(Note(taken_at=taken_at, content=template.format(**_template_values(rng))))
        # A phone call documents care but is not a visit.
        if template != TELEPHONE_NOTE:
            last_visit = note_date
    return notes, last_visit


def _build_patient(rng: random.Random, index: int) -> Patient:
    first = rng.choice(seed_data.FIRST_NAMES)
    last = rng.choice(seed_data.LAST_NAMES)
    city, state, postal_code, area_code = rng.choice(seed_data.LOCATIONS)
    age_days = rng.randint(18 * 365, 92 * 365)

    # About 10% have no recorded blood type. The rest follow approximate US frequencies.
    blood_type = None
    if rng.random() > 0.10:
        weights = seed_data.BLOOD_TYPE_WEIGHTS
        blood_type = BloodType(rng.choices(list(weights), weights=list(weights.values()))[0])

    note_count = rng.choices([0, 1, 2, 3, 4, 5], weights=[8, 15, 25, 25, 15, 12])[0]
    if note_count == 0:
        # A new patient who hasn't been seen yet: intake isn't done, so both lists are unknown.
        conditions, allergies = None, None
        notes, last_visit = [], None
    else:
        conditions = _pick_conditions(rng, age_days // 365)
        allergies = _pick_allergies(rng)
        notes, last_visit = _build_notes(rng, conditions, note_count)

    return Patient(
        first_name=first,
        last_name=last,
        date_of_birth=ANCHOR_DATE - timedelta(days=age_days),
        # 555-0100 through 555-0199 is reserved for fictional use.
        phone=f"({area_code}) 555-01{rng.randint(0, 99):02d}",
        # example.com is reserved (RFC 2606) and can never deliver real mail.
        email=f"{first}.{last}{index}@example.com".lower(),
        street=f"{rng.randint(10, 9999)} {rng.choice(seed_data.STREET_NAMES)}",
        city=city,
        state=state,
        postal_code=postal_code,
        blood_type=blood_type,
        allergies=allergies,
        conditions=conditions,
        status=rng.choices(list(PatientStatus), weights=[82, 14, 4])[0],
        last_visit_date=last_visit,
        notes=notes,
    )


def seed(db: Session) -> int:
    """Insert the synthetic patients if the patients table is empty, and return how many.

    Deleted patients are still rows, so the seed never adds data on top of retained records.
    Everything is saved in one transaction: either all patients and notes are saved, or none.
    """
    if db.scalar(select(Patient.id).limit(1)) is not None:
        return 0

    rng = random.Random(RANDOM_SEED)
    patients = [_build_patient(rng, i) for i in range(1, PATIENT_COUNT + 1)]
    db.add_all(patients)
    db.commit()
    return len(patients)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [seed] %(message)s")
    with SessionLocal() as db:
        inserted = seed(db)
    if inserted:
        logger.info("Inserted %d synthetic patients", inserted)
    else:
        logger.info("Patients already present; skipping seed")


if __name__ == "__main__":
    main()
