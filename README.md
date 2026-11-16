# WordWise

WordWise is a child-friendly vocabulary-learning web app for students from Kindergarten through Grade 12. Many children's vocabulary stays small because practice is irregular and nobody tracks which words stuck. WordWise gives a child a small daily set of age-appropriate words and tracks what they have learned.

## What it does

- **Profiles.** A parent creates one or more child profiles on one browser (nickname, grade, daily word goal). There are no accounts or logins.
- **Learning.** The child sees a few words a day, one at a time, with the meaning and an example sentence.
- **Quiz.** After learning, a 4-option multiple-choice quiz checks each word and gives immediate feedback with an explanation.
- **Mastery and review.** A word moves from `NEW` to `LEARNING` to `MASTERED` after 3 correct answers in a row. A wrong answer resets the streak and flags the word for review.
- **Parent dashboard.** Per child: activity, vocabulary growth, quiz accuracy, words needing review and recent sessions.
- **Persistence.** Profiles, sessions, answers and mastery live in PostgreSQL behind a FastAPI REST API (`/api/v1`, OpenAPI at `/docs`).
- **Content.** A curated, validated vocabulary of 650 words (50 per grade for K to 12 is the release target; 500 for Kindergarten to Grade 9 are loaded so far).

The full specification is `_docs/plan.md`; the architecture is `_docs/architecture.md`.

## How it was built

The project is built by an AI agent team following a written process, with every unit of work tracked as a public GitHub issue with acceptance criteria.

- **Spec first.** `_docs/plan.md` defines behavior and API before code; `_docs/tasks.md` breaks it into tasks.
- **Public tracker.** [Issues](https://github.com/gaganarora23/wordwiseai/issues) hold the backlog, each with acceptance criteria; `mvp` and `post-mvp` labels mark scope; commits and PRs reference issue numbers.
- **Agent team.** An orchestrator (the main session) launches three subagents per task: a **PM** that grooms the issue, an **engineer** that implements it, and a **QA engineer** that checks it against the acceptance criteria and posts PASS or FAIL. On FAIL the engineer retries with QA's comment. Roles are in `_docs/team/`, the lifecycle is in `_docs/process.md`.
- **Context management.** `AGENTS.md` at the root points to modular docs in `_docs/`, with `backend/AGENTS.md` and `frontend/AGENTS.md` for each part.

## Run the app locally

## Run everything with Docker (one command)

**Prerequisite:** Docker (running). From the repository root:

```sh
docker compose up --build         # database, backend and frontend
```

No setup file is needed: without a `.env`, Compose uses local-development defaults for the database (user `wordwise`, password `change-me`, database `wordwise`), and the database port is published on `127.0.0.1` only. To use your own values, copy `.env.example` to `.env` and edit it; never use the defaults outside local development.

This starts PostgreSQL, then the backend (which applies the migrations, loads the vocabulary and serves the API on `http://localhost:8000`, docs at `/docs`), then the frontend on `http://localhost:8080`. Open `http://localhost:8080`, create a profile and click its tile to see the words for its grade. Stop with `Ctrl+C`; add `-d` to run in the background and `docker compose down` to stop (`down -v` also deletes the database). The frontend calls the backend at `http://localhost:8000` (baked in at build time via the `VITE_API_URL` build arg in `docker-compose.yml`).

The sections below describe running the pieces without Docker, for development.

**Prerequisites:** Docker (running), [uv](https://docs.astral.sh/uv/), Node 24 and bun 1.4.

**Current state.** The backend has the database schema, the vocabulary tooling, `GET /api/v1/health` and `GET /api/v1/grades/{grade}/words`; the profile, session and quiz endpoints are not built yet (tasks #17, #20 onwards, tracked as issues). The frontend therefore keeps profiles in the browser's local storage (mock service, `frontend/src/services/index.ts`) but reads the words from the backend: pick a profile and the "words" page lists the vocabulary of that profile's grade, loaded from PostgreSQL through the API. Both are started below so each can be checked on its own.

Steps 1 and 2 run from the repository root, steps 3 to 5 from `backend/`, step 6 from `frontend/` (each step says where). Steps 5 and 6 each keep a terminal busy, so use a separate terminal for each.

**1. Configuration** (once). The placeholders in `.env.example` work as-is for local development:

```sh
cp .env.example .env
```

**2. Database.** Starts PostgreSQL 18 in Docker and waits until it is healthy:

```sh
docker compose up -d --wait db
```

**3. Backend dependencies and schema** (safe to repeat):

```sh
cd backend
uv sync
uv run alembic upgrade head     # creates the tables
```

**4. Load the vocabulary** (still in `backend/`; safe to repeat):

```sh
uv run python -m app.services.vocabulary_ingestion
```

Expected last lines: `Created: 500, updated: 0, unchanged: 0` and `Release target not reached: 500 of 650 words`. A second run prints `unchanged: 500`. To use the development fixture words instead, pass their path: `uv run python -m app.services.vocabulary_ingestion fixtures/vocabulary`.

**5. Start the backend** (terminal 1, in `backend/`):

```sh
uv run uvicorn app.main:app
```

Check it in a browser or with curl:

- `http://localhost:8000/api/v1/health` returns `{"status":"ok"}`
- `http://localhost:8000/docs` is the interactive API documentation

**6. Start the frontend** (terminal 2, from the repository root):

```sh
cd frontend
bun install --frozen-lockfile   # first time, and after dependency changes
bun run dev
```

Open `http://localhost:8080`. You should see "WordWise — Who's learning today?". Create a profile, then click its tile: the page lists that grade's words (50 per grade), served by the backend from PostgreSQL. If the backend is not running you get "We couldn't load the words" with a retry button. The frontend talks to `http://localhost:8000` unless `VITE_API_URL` is set.

**Check the loaded vocabulary** (from the repository root):

```sh
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select grade, count(*) from words group by grade order by grade;"'
```

It lists 50 words for each of K and 1 to 9.

**Stop.** Press `Ctrl+C` in the backend and frontend terminals, then `docker compose down` (keeps the data) or `docker compose down -v` (also deletes the database; the next start needs steps 3 and 4 again).

**Troubleshooting.**

- `Configuration error: DATABASE_URL must be set ...`: step 1 was skipped, or you are running a command outside the repository checkout.
- Port 5432, 8000 or 8080 already in use: stop what is using it. For PostgreSQL you can instead set `DB_PORT=5433` in `.env` and use port 5433 in `DATABASE_URL`.
- `Cannot connect to the database` or the tests asking for `docker compose up -d --wait db`: Docker is not running, or step 2 was skipped.
- `Database is not migrated`: run step 3.
- Tests: `make test` from the repository root (needs steps 1 and 2 and `cd frontend && bun install` once).

## Database

PostgreSQL 18 runs in Docker Compose with a named volume (`db_data`), published on `127.0.0.1` only.

```sh
cp .env.example .env              # placeholders work as-is for local development
docker compose up -d --wait db    # starts PostgreSQL and waits until healthy
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'   # open psql
```

`POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` default to `wordwise`, `change-me` and `wordwise` (local development only); set them in `.env` to override.

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

**Vocabulary loading.** `cd backend && uv run python -m app.services.vocabulary_ingestion [PATH ...]` validates the vocabulary files and loads them into `words` in one transaction, idempotently and by stable id. See [Loading into the database](backend/data/README.md#loading-into-the-database) for the exit codes, the removed-words rule and the 650-word target line.

A development-only vocabulary (154 words, not release content) is in `backend/fixtures/vocabulary/`; see its README.

Connection settings: connect timeout is 5 seconds (`connect_args={"connect_timeout": 5}`) and `pool_pre_ping=True`; both are defined in `backend/app/config.py` and used in `backend/app/db.py`. Database tests need the Compose database (`docker compose up -d --wait db`); without it they fail with that command in the message.

## Testing

`make test` from the repo root runs the backend suite (`cd backend && uv run pytest`), then the frontend suite. Backend integration tests run against real PostgreSQL, never SQLite.

**Database.** Locally PostgreSQL is the Compose service: `docker compose up -d --wait db`. In CI it will be a service container, configured in #47. The harness (`backend/tests/conftest.py`, plumbing in `harness.py`) creates its own `wordwise_test_<random>` database on the same server as `DATABASE_URL`, runs `alembic upgrade head` on it once per pytest run, and drops it at the end, so the development database is never read, truncated or migrated. The `DATABASE_URL` user needs the `CREATEDB` privilege (the Compose user and a CI service container have it). If PostgreSQL is down, tests that use the harness fail (not skip) with `docker compose up -d --wait db` in the message; tests that need no database still pass. The database is dropped even when a test fails; a killed process (`kill -9`) can leave a `wordwise_test_*` database behind, which you can drop by hand.

**Fixtures** (`backend/tests/conftest.py`):

- `clean_db`: the migrated test database as an SQLAlchemy `Engine`. All seven tables are emptied (`TRUNCATE`) before and after every test, so rows the code under test committed do not leak. `alembic_version` is kept.
- `db_session`: a `Session` on that database for your own inserts and queries. Commit to make rows visible to routes.
- `client`: a `TestClient` for `app.main.app` with `get_session` overridden (via `app.dependency_overrides`) to sessions on the test database. The override is removed after each test.
- Helpers in `backend/tests/helpers.py`: `insert_child`, `insert_word`, `insert_session_with_words`. They take a connection or session, do not commit, return the new id, and accept keyword overrides.

```python
from tests.helpers import insert_child

def test_child_is_visible_to_the_api(client, db_session):
    child_id = insert_child(db_session, nickname="Sam")
    db_session.commit()
    assert client.get(f"/api/v1/children/{child_id}").status_code == 200  # illustrative route, arrives with #17
```

`test_harness.py` proves the harness: tables are empty at the start of every test, committed rows do not leak, and the failure behaviour above.
