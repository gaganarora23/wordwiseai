# wordwiseai

## Database

PostgreSQL 18 runs in Docker Compose with a named volume (`db_data`), published on `127.0.0.1` only.

```sh
cp .env.example .env              # placeholders work as-is for local development
docker compose up -d --wait db    # starts PostgreSQL and waits until healthy
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'   # open psql
```

Compose refuses to start if `POSTGRES_USER`, `POSTGRES_PASSWORD` or `POSTGRES_DB` is missing or empty.

**Persistence check.** Data survives `restart`, `stop`/`start` and `down`/`up`:

```sh
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "create table t(x int); insert into t values (1);"'
docker compose restart db
docker compose stop db && docker compose start db
docker compose down && docker compose up -d --wait db
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select * from t;"'   # run after each step; still returns the row
```

**Reset.** `docker compose down -v` removes the volume and **deletes all database data**; the next `up` starts empty.

**Port conflict.** If a local PostgreSQL already uses 5432, set `DB_PORT=5433` in `.env` (and the port in `DATABASE_URL`).

**Password change.** Changing `POSTGRES_PASSWORD` in `.env` after the volume exists does not change the stored password. Run `docker compose down -v` (deletes data) or `ALTER USER ... PASSWORD '...'`.

**Backend configuration.** The backend reads two environment variables (real environment wins over the repo-root `.env`):

- `DATABASE_URL` (required): must start with `postgresql+psycopg://`. The backend refuses to start with a one-line error if it is missing or invalid. The database itself does not need to be running for the app to start or for `GET /api/v1/health` to answer.
- `CORS_ORIGINS` (optional): comma-separated browser origins allowed via CORS; unset or empty allows none.

Run the backend against the Compose database:

```sh
cp .env.example .env && docker compose up -d --wait db
cd backend && uv sync && uv run uvicorn app.main:app
```

Connection settings: connect timeout is 5 seconds (`connect_args={"connect_timeout": 5}`) and `pool_pre_ping=True`; both are defined in `backend/app/config.py` and used in `backend/app/db.py`. Database tests need the Compose database (`docker compose up -d --wait db`); without it they fail with that command in the message.
