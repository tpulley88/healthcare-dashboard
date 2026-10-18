import pytest
from pydantic import ValidationError

from app.config import DEFAULT_OPENAI_MODEL, Settings

DATABASE_URL = "postgresql+psycopg://user:pass@db:5432/app"


@pytest.mark.parametrize("timezone", ["Mars/Olympus_Mons", "../etc/passwd", ""])
def test_unknown_practice_timezone_is_rejected(timezone):
    with pytest.raises(ValidationError, match="Must be an IANA timezone name"):
        Settings(database_url=DATABASE_URL, practice_timezone=timezone)


def test_practice_timezone_defaults_to_new_york():
    assert Settings(database_url=DATABASE_URL).practice_timezone == "America/New_York"


@pytest.mark.parametrize("key", ["", "   "])
def test_blank_openai_key_means_not_configured(key):
    assert Settings(database_url=DATABASE_URL, openai_api_key=key).openai_api_key is None


def test_blank_openai_model_falls_back_to_default():
    settings = Settings(database_url=DATABASE_URL, openai_model="")
    assert settings.openai_model == DEFAULT_OPENAI_MODEL


def test_openai_key_is_hidden_when_settings_are_printed():
    settings = Settings(database_url=DATABASE_URL, openai_api_key="sk-test-not-real")
    assert "sk-test-not-real" not in repr(settings)
    assert settings.openai_api_key.get_secret_value() == "sk-test-not-real"
