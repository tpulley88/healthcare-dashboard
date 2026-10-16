from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


# Loaded from environment variables; missing or invalid values raise at import time.
class Settings(BaseSettings):
    # PostgresDsn rejects empty, malformed, and non-Postgres URLs before SQLAlchemy sees them.
    database_url: PostgresDsn


settings = Settings()
