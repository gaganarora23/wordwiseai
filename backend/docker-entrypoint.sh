#!/bin/sh
# Prepare the database, then serve the API. Both steps are safe to repeat.
set -e
alembic upgrade head
python -m app.services.vocabulary_ingestion
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
