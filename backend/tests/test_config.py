import pytest
from pydantic import ValidationError

from app.config import Settings

DATABASE_URL = "postgresql+psycopg://user:pass@db:5432/app"


@pytest.mark.parametrize("timezone", ["Mars/Olympus_Mons", "../etc/passwd", ""])
def test_unknown_practice_timezone_is_rejected(timezone):
    with pytest.raises(ValidationError, match="Must be an IANA timezone name"):
        Settings(database_url=DATABASE_URL, practice_timezone=timezone)


def test_practice_timezone_defaults_to_new_york():
    assert Settings(database_url=DATABASE_URL).practice_timezone == "America/New_York"
