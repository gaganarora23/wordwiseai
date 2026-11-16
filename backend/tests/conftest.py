import os
from pathlib import Path

# The app needs a database URL at import time (no database has to be running).
# Without a repo-root .env, fall back to the .env.example value.
if not (Path(__file__).resolve().parents[2] / ".env").exists():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://wordwise:change-me@localhost:5432/wordwise",
    )
