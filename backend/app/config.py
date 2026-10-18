"""Application settings, read from environment variables.

Settings are checked when this module is imported, and the app imports it at startup.
A missing or invalid value therefore stops the server before it accepts any requests.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_core import PydanticCustomError
from pydantic_settings import BaseSettings

DEFAULT_OPENAI_MODEL = "gpt-5-mini"


class Settings(BaseSettings):
    # PostgresDsn rejects empty, malformed, and non-Postgres URLs before SQLAlchemy sees them.
    database_url: PostgresDsn

    # Summaries show calendar dates in the practice's local time.
    # In UTC, a note written at 9 PM in New York would show the next day's date.
    practice_timezone: str = "America/New_York"

    # Optional. Without a key, generated summaries are switched off and only the template is used.
    # SecretStr keeps the key out of logs and error messages.
    openai_api_key: SecretStr | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL

    # Compose passes unset variables as empty strings. Treat those as "not set".
    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _blank_key_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("openai_model", mode="before")
    @classmethod
    def _blank_model_is_default(cls, value: object) -> object:
        return DEFAULT_OPENAI_MODEL if isinstance(value, str) and not value.strip() else value

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
