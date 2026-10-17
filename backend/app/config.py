"""Application settings, read from environment variables.

Settings are checked when this module is imported, and the app imports it at startup.
A missing or invalid value therefore stops the server before it accepts any requests.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import PostgresDsn, field_validator
from pydantic_core import PydanticCustomError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgresDsn rejects empty, malformed, and non-Postgres URLs before SQLAlchemy sees them.
    database_url: PostgresDsn

    # Summaries show calendar dates in the practice's local time.
    # In UTC, a note written at 9 PM in New York would show the next day's date.
    practice_timezone: str = "America/New_York"

    @field_validator("practice_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise PydanticCustomError(
                "value_error", "Must be an IANA timezone name, such as America/New_York"
            ) from None
        return value

    @property
    def practice_tz(self) -> ZoneInfo:
        return ZoneInfo(self.practice_timezone)


settings = Settings()
