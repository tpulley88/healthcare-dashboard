FROM python:3.12-slim

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
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
# The entrypoint migrates and seeds, then execs CMD.
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
