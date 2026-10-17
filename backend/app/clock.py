"""The one place the app reads the current time.

"Today" always means the calendar date at the practice, in PRACTICE_TIMEZONE.
Ages, date checks, and summaries all use it, so they agree with each other,
even in the hours when the UTC date has already changed but the local date hasn't.
Tests replace `now` to pin an exact instant.
"""

from datetime import UTC, date, datetime

from app.config import settings


def now() -> datetime:
    return datetime.now(UTC)


def practice_today() -> date:
    return practice_date(now())


def practice_date(moment: datetime) -> date:
    """The calendar date at the practice when `moment` happened."""
    return moment.astimezone(settings.practice_tz).date()
