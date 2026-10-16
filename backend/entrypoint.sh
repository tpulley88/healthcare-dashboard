#!/bin/sh
# Container startup: migrate, seed, then hand off to the main process.
# Any failing step stops the container.
set -e

alembic upgrade head
python -m app.seed

# exec makes the server PID 1 so it receives the container's stop signal directly.
exec "$@"
