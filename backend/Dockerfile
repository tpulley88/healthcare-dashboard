FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached until the lockfile changes.
# --frozen fails the build if uv.lock is stale.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home appuser
ENV PATH="/app/.venv/bin:$PATH"


# Test image: adds dev dependencies and tests. Run with `docker compose run --rm test`.
FROM base AS test
RUN uv sync --frozen --no-install-project
COPY tests ./tests
USER appuser
# Skip the migrate-and-seed entrypoint; the test fixtures migrate their own database.
ENTRYPOINT []
# The cache plugin is off: /app is root-owned and a throwaway container has no use for it.
CMD ["pytest", "-p", "no:cacheprovider"]


FROM base AS runtime
USER appuser
EXPOSE 8000
# The entrypoint migrates and seeds, then execs CMD.
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
