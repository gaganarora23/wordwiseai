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

**Migrations.** The schema is owned by Alembic (`backend/migrations/`); the URL comes from `DATABASE_URL`, never from `alembic.ini`. With the database up:

```sh
cd backend && uv run alembic upgrade head     # create/update the schema (safe to repeat)
cd backend && uv run alembic downgrade base   # roll back: drops quiz_results, word_mastery, answers, session_words, sessions, words and children
cd backend && uv run alembic check            # models and migration agree
```

**Sessions.** `sessions`, `session_words` and `answers` (migration `0002`) enforce the session rules in PostgreSQL: one `in_progress` session per child (partial unique index), status and `completed_at`/`abandoned_at` agree, one answer per word per session, and an answer needs a matching `session_words` row (composite foreign key). Deleting a child or session cascades; a word used by a session cannot be deleted. `answers.selected_option` uses the same 1 to 4 numbering as `words.correct_option` (and `option_1` to `option_4`).

**Results and mastery.** `quiz_results` and `word_mastery` (migration `0003`) enforce in PostgreSQL: one result per session (primary key `session_id`) and one mastery row per child and word (primary key `(child_id, word_id)`); `word_mastery.status` is exactly `NEW`, `LEARNING` or `MASTERED`, `consecutive_correct` is 0 to 3, and status and progress agree (`NEW` is 0, never practiced, no review; `LEARNING` is 0 to 2 and practiced; `MASTERED` is 3 and practiced). `needs_review` is a separate boolean, not a status value. A result's `score` equals `correct_count`, the counts are not negative and sum to 1 to 10, and `review_word_ids` (`uuid[]`, default empty, no NULL elements) has between `incorrect_count` and `correct_count + incorrect_count` entries. Deleting a child cascades to its mastery rows, and deleting a session cascades to its result only (mastery is per child and word); a word with a mastery row cannot be deleted. Not enforced here, and left to #27: that the session is completed, that counts match the answers, that review ids are distinct and belong to the session, and that the writing code never stores a streak above 3 (rule logic is #21).

**Answer options.** A word stores its four options as columns `option_1` to `option_4` (all NOT NULL, not blank) plus `correct_option` (check: 1 to 4). PostgreSQL therefore enforces exactly four options and exactly one correct one with plain check constraints, without a child table or triggers. SQLAlchemy 2.1, psycopg 3.3 and Alembic 1.20 work together on PostgreSQL 18.

Connection settings: connect timeout is 5 seconds (`connect_args={"connect_timeout": 5}`) and `pool_pre_ping=True`; both are defined in `backend/app/config.py` and used in `backend/app/db.py`. Database tests need the Compose database (`docker compose up -d --wait db`); without it they fail with that command in the message.
