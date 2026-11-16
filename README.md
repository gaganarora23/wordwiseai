# WordWise

WordWise is a child-friendly vocabulary-learning web app for students from Kindergarten through Grade 12. Many children's vocabulary stays small because practice is irregular and nobody tracks which words stuck. WordWise gives a child a small daily set of age-appropriate words and tracks what they have learned.

**Live demo:** https://wordwise-web.onrender.com (free tier: the first request after idle takes about a minute). API docs: https://wordwise-api-xji2.onrender.com/docs

## Quick start

**Prerequisite:** [Docker](https://docs.docker.com/get-docker/) installed **and running** (start Docker Desktop first; otherwise you get `Cannot connect to the Docker daemon`).

| I want to... | Run (from the repository root) | Then |
|---|---|---|
| Run the whole app (database, backend, frontend) | `docker compose up --build` | Open http://localhost:8080 (UI). API: http://localhost:8000/docs |
| Run all tests (backend and frontend) | `make test` | Needs Docker, [uv](https://docs.astral.sh/uv/), Node 24 and [bun](https://bun.sh) 1.4. Installs dependencies and starts the database itself. |
| Stop the app | `Ctrl+C`, then `docker compose down` | `docker compose down -v` also deletes the database |

No `.env` file is needed; local-development defaults are built in. First build takes a few minutes. Details: [Run the app locally](#run-the-app-locally), [Testing](#testing), [API](#api), [Deployment](#deployment).

## What it does

- **Profiles.** A parent creates one or more child profiles on one browser (nickname, grade, daily word goal). There are no accounts or logins.
- **Learning.** The child sees a few words a day, one at a time, with the meaning and an example sentence.
- **Quiz.** After learning, a 4-option multiple-choice quiz checks each word and gives immediate feedback with an explanation.
- **Mastery and review.** A word moves from `NEW` to `LEARNING` to `MASTERED` after 3 correct answers in a row. A wrong answer resets the streak and flags the word for review.
- **Parent dashboard.** Per child: activity, vocabulary growth, quiz accuracy, words needing review and recent sessions.
- **Persistence.** Profiles, sessions, answers and mastery live in PostgreSQL behind a FastAPI REST API (`/api/v1`, OpenAPI at `/docs`).
- **Content.** A curated, validated vocabulary of 650 words (50 per grade for K to 12 is the release target; 500 for Kindergarten to Grade 9 are loaded so far).

The full specification is [`_docs/plan.md`](_docs/plan.md); the architecture is [`_docs/architecture.md`](_docs/architecture.md). Tech stack: React (Vite, TanStack, bun) frontend, FastAPI + SQLAlchemy + Alembic backend (Python 3.13, uv), PostgreSQL 18, Docker Compose, GitHub Actions, Render.

### What works today

The course delivery builds this in vertical slices, tracked as issues (`mvp` and `post-mvp` labels).

| Area | State |
|---|---|
| Profiles: create, list, view, edit, delete | **Works end to end** (frontend, API, PostgreSQL) |
| Vocabulary for each grade (650-word release target; 500 loaded) | **Works end to end**: the profile's "See your words" page lists the grade's words from the API |
| Daily learning sessions, quiz, mastery and review, results, parent dashboard | Not built on the backend yet (issues #20 to #32, #38 to #41); the quiz and dashboard code in the frontend still runs on a browser mock |

## How it was built

The project is built by an AI agent team following a written process, with every unit of work tracked as a public GitHub issue with acceptance criteria.

- **Spec first.** [`_docs/plan.md`](_docs/plan.md) defines behavior and API before code; [`_docs/tasks.md`](_docs/tasks.md) breaks it into tasks.
- **Public tracker.** [Issues](https://github.com/gaganarora23/wordwiseai/issues) hold the backlog, each with acceptance criteria; `mvp` and `post-mvp` labels mark scope; commits and PRs reference issue numbers.
- **Agent team.** An orchestrator (the main session) launches three subagents per task: a **PM** that grooms the issue, an **engineer** that implements it, and a **QA engineer** that checks it against the acceptance criteria and posts PASS or FAIL. On FAIL the engineer retries with QA's comment. Roles and their limits are in [`docs/agents.md`](docs/agents.md) and [`_docs/team/`](_docs/team/), the lifecycle is in [`_docs/process.md`](_docs/process.md), and branch, PR and CI conventions are in [`docs/process.md`](docs/process.md).
- **Context management.** [`AGENTS.md`](AGENTS.md) at the root points to modular docs in [`_docs/`](_docs/) and [`docs/`](docs/), with [`backend/AGENTS.md`](backend/AGENTS.md) and [`frontend/AGENTS.md`](frontend/AGENTS.md) for each part.

## Run the app locally

### Option A: everything with Docker (one command)

**Prerequisite:** Docker (running). From the repository root:

```sh
docker compose up --build         # database, backend and frontend
```

No setup file is needed: without a `.env`, Compose uses local-development defaults for the database (user `wordwise`, password `change-me`, database `wordwise`), and the database port is published on `127.0.0.1` only. To use your own values, copy `.env.example` to `.env` and edit it; never use the defaults outside local development.

This starts PostgreSQL, then the backend (which applies the migrations, loads the vocabulary and serves the API on `http://localhost:8000`, docs at `/docs`), then the frontend on `http://localhost:8080`. Open `http://localhost:8080`, add a learner (nickname, grade, daily goal), and click the tile to see the words for its grade; you can also edit and delete the profile. Profiles are stored in PostgreSQL, so they survive a reload and a restart. Stop with `Ctrl+C`; add `-d` to run in the background and `docker compose down` to stop (`down -v` also deletes the database). The frontend calls the backend at `http://localhost:8000` (baked in at build time via the `VITE_API_URL` build arg in `docker-compose.yml`).

### Option B: run the pieces without Docker (for development)

Only the database runs in Docker here; the backend and frontend run on your machine.

**Prerequisites:** Docker (running), [uv](https://docs.astral.sh/uv/) (installs Python 3.13 for you), Node 24 and bun 1.4.

**Current state.** The backend has the database schema, the vocabulary tooling, `GET /api/v1/health`, `GET /api/v1/grades/{grade}/words` and the profile endpoints (create, list, get, update, delete: see [API](#api)). The frontend reads and writes profiles through the API, so they are stored in PostgreSQL, and its "words" page lists the vocabulary of the profile's grade from the API. The session, quiz and dashboard endpoints are not built yet (tasks #20 onwards, tracked as issues), so those screens still use the frontend's built-in mock service (`frontend/src/services/index.ts`; set `VITE_USE_MOCK=true` to run the whole frontend on the mock, without the backend). Both parts are started below so each can be checked on its own.

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

Open `http://localhost:8080`. You should see "WordWise — Who's learning today?". Click "Add a learner" and save a profile (it is stored in PostgreSQL), then click its tile: the page lists that grade's words (50 per grade). If the backend is not running the profile list shows "We couldn't load profiles" with a retry button. The frontend talks to `http://localhost:8000` unless `VITE_API_URL` is set.

**Check the loaded vocabulary** (from the repository root):

```sh
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select grade, count(*) from words group by grade order by grade;"'
```

It lists 50 words for each of K and 1 to 9.

**Stop.** Press `Ctrl+C` in the backend and frontend terminals, then `docker compose down` (keeps the data) or `docker compose down -v` (also deletes the database; the next start needs steps 3 and 4 again).

**Troubleshooting.**

- `Configuration error: DATABASE_URL must be set ...`: step 1 was skipped, or you are running a command outside the repository checkout.
- Port 5432, 8000 or 8080 already in use: stop what is using it. For PostgreSQL you can instead set `DB_PORT=5433` in `.env` and use port 5433 in `DATABASE_URL`.
- `Cannot connect to the Docker daemon` (from `docker compose` or `make test`): Docker Desktop is not running. Start it (for example after a restart), wait until it reports running, and retry.
- `Cannot connect to the database` or the tests asking for `docker compose up -d --wait db`: Docker is not running, or step 2 was skipped.
- `Database is not migrated`: run step 3.
- Tests: `make test` from the repository root. It installs the dependencies and starts the database if needed (needs Docker, or a reachable PostgreSQL; no other steps).

## API

Interactive documentation is served at `http://localhost:8000/docs` (OpenAPI 3.1). Base path `/api/v1`.

| Method and path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /health` | Liveness | `200` | |
| `GET /grades/{grade}/words` | Curated words of one grade (K, 1 to 12) with answer options | `200` (empty list if none) | `422` unknown grade |
| `POST /profiles` | Create a profile: `{nickname, grade, daily_goal}` | `201` | `422` |
| `GET /profiles` | All profiles (empty list if none) | `200` | |
| `GET /profiles/{profile_id}` | One profile | `200` | `404` unknown, `422` malformed id |
| `PUT /profiles/{profile_id}` | Replace nickname, grade and daily goal; `updated_at` changes | `200` | `404`, `422` |
| `DELETE /profiles/{profile_id}` | Delete the profile and, by database cascade, its sessions, answers, results and mastery | `204` | `404` (also on the second delete) |

A profile is `{id, nickname, grade, daily_goal, created_at, updated_at}`. Validation: nickname 1 to 20 characters (surrounding whitespace is trimmed), grade `K` or `1` to `12`, daily goal `5` or `10`; unknown or extra fields are rejected with `422`. Browsers may call the API from the origins in `CORS_ORIGINS` with `GET`, `POST`, `PUT` and `DELETE`.

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

- `DATABASE_URL` (required): must start with `postgresql+psycopg://`; `postgresql://` and `postgres://` (what hosts such as Render provide) are accepted and rewritten to `postgresql+psycopg://`. The backend refuses to start with a one-line error if it is missing or invalid. The database itself does not need to be running for the app to start or for `GET /api/v1/health` to answer.
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

## Deployment

WordWise is deployed to [Render](https://render.com) (free tier) from the Blueprint in [`render.yaml`](render.yaml): one PostgreSQL database (`wordwise-db`, PostgreSQL 18, Render's newest major and allowed on the free plan) and two Docker web services, `wordwise-api` (backend) and `wordwise-web` (frontend).

**Public URLs:**

- App: https://wordwise-web.onrender.com
- API: https://wordwise-api-xji2.onrender.com (interactive docs at `/docs`)

The first request after 15 minutes idle takes about a minute (free-tier cold start); wait and reload. The uptime alert keeps the API mostly warm, but the web app still sleeps.

Steps (done once, by the project owner):

1. Sign in at [render.com](https://render.com) and connect your GitHub account.
2. New > Blueprint, pick the `gaganarora23/wordwiseai` repo and branch, then Apply. Render creates the database and both services and builds them.
3. Render added a suffix to the API name because `wordwise-api` was already taken, so the API URL is `https://wordwise-api-xji2.onrender.com`, not the one a name alone predicts. The web service kept `https://wordwise-web.onrender.com`. `CORS_ORIGINS` (API) holds the web origin; `VITE_API_URL` (web) holds the API URL and is baked into the frontend at build time, so a wrong value leaves the page stuck on "Loading profiles". If a service is recreated and its URL changes: copy the URL from the service page, then on `wordwise-web` open Environment, edit `VITE_API_URL`, Save, then Manual Deploy (or the deploy hook) to rebuild; update `render.yaml` and the URLs above to match.
4. Auto-deploy is off. Deploys are triggered from GitHub Actions through deploy hooks; copy each service's deploy hook URL (Settings) into GitHub secrets as described in [`docs/deployment.md`](docs/deployment.md).

Things to know:

- **Cold start.** Free web services sleep after 15 minutes idle; the first request afterwards takes about a minute. With the [uptime alert](#uptime-alert) running, the API is mostly warm; the web frontend is not pinged and still cold-starts.
- **Database expiry.** A free Render PostgreSQL database expires 30 days after creation, so the shared demo data (every profile) is lost then unless the database is upgraded to a paid plan first. To recreate it, follow [If the free database expired](docs/deployment.md#if-the-free-database-expired-after-30-days).
- **Vocabulary.** On start the backend loads 500 of the 650 target words (K to 9; Grades 10 to 12 are issue #16), logging `Created: 500` the first time and `unchanged: 500` afterwards.
- **Shared demo.** There is no authentication; anyone with the link sees and edits the same profiles, so real children's data must not be entered. The app says this on the home page.
- **Database URL.** Render's `postgresql://` connection string is accepted; the backend rewrites it to `postgresql+psycopg://`.

## Uptime alert

A scheduled GitHub Actions workflow (`.github/workflows/uptime-alert.yml`) is an alert on user impact. It exercises what a child would hit, not CPU or memory: `GET /api/v1/health` must return 200, and `GET /api/v1/grades/5/words` must return 200 with exactly 50 words (the API is reachable and the words list loads from PostgreSQL, so this also catches a database outage). Each request waits up to about 2 minutes (tolerating a cold start); a failed check is retried once after 10 seconds.

**Does not cover:** real-user error rates, the web frontend (it is never requested), other endpoints, or any paging beyond GitHub's failed-workflow email, which depends on the owner's GitHub notification settings.

**Frequency and footprint.** The cron is `*/15 * * * *`: every 15 minutes, 2 requests per run, so about 96 runs and 192 requests a day (up to 4 requests in a run where a check fails and retries). That is tiny. No Render rate limit is documented, and none is claimed here.

**Render free-tier trade-off.** Free web services sleep after about 15 minutes idle, so a check every 15 minutes keeps the API awake roughly around the clock. That uses most of the monthly free instance hours (about 750 hours a month across the workspace; approximate, the owner should confirm in the Render dashboard). The web frontend is not pinged and still sleeps. The owner has chosen to accept this trade-off.

**Detection delay.** In the worst case a failure is noticed about 15 minutes after it starts, plus GitHub's scheduling delay. GitHub may delay or skip scheduled runs under load, so detection is neither instant nor guaranteed.

**Change or stop it.** To change the frequency, edit the `cron` line in `.github/workflows/uptime-alert.yml`. To turn it off: Actions, "Uptime alert", "Disable workflow".

- **Where a failure shows up:** a red run in the repository's Actions tab, and GitHub's failed-workflow email to the repo owner.
- **Run it by hand:** Actions, "Uptime alert", "Run workflow", with an optional `api_url` (empty checks `https://wordwise-api-xji2.onrender.com`).
- **Run it locally:** `bash .github/scripts/check-user-journey.sh [url]` (needs bash, curl and jq).

## Testing

```sh
make test                          # everything: backend (pytest) + frontend (Vitest)
cd backend && uv run pytest        # backend only (needs the database: docker compose up -d --wait db)
cd frontend && bun run test        # frontend only
```

The backend suite has unit tests (validators, config, schemas) and integration tests that call the API against a real PostgreSQL database (`backend/tests/`); the frontend suite covers the HTTP service, routing and components (`frontend/src/test/`). CI runs the same `make test` on every pull request.

`make test` from the repo root is the single command, and works from a fresh clone. It runs `uv sync --frozen` (backend) and `bun install --frozen-lockfile` (frontend), starts the Compose database if none is reachable (`docker compose up -d --wait db`, never `down` or `-v`, so existing data is untouched), then runs the backend suite (`cd backend && uv run pytest`) and the frontend suite. Both suites always run; the exit status is non-zero if either fails. Backend integration tests run against real PostgreSQL, never SQLite. The separate commands (`cd backend && uv run pytest`, `cd frontend && bun run test`) still work.

Database selection by `make test`: a `DATABASE_URL` exported in your shell or set in `.env` is used as is and never overridden. If neither is set, the Compose defaults (`wordwise` / `change-me` / `wordwise` on `localhost`) are used with `DB_PORT` (environment, then `.env`, default 5432); the URL is passed to the test run only and no file is written. If the host and port already answer, or `CI=true`, no Docker command is run. If Docker is not installed or not running, `make test` prints one line saying so and exits non-zero. If the database never becomes healthy, set `DB_PORT` (see Troubleshooting).

**Database.** Locally PostgreSQL is the Compose service, started for you by `make test` (or by hand: `docker compose up -d --wait db`). In CI it is a service container (`.github/workflows/ci.yml`). The harness (`backend/tests/conftest.py`, plumbing in `harness.py`) creates its own `wordwise_test_<random>` database on the same server as `DATABASE_URL`, runs `alembic upgrade head` on it once per pytest run, and drops it at the end, so the development database is never read, truncated or migrated. The `DATABASE_URL` user needs the `CREATEDB` privilege (the Compose user and a CI service container have it). If PostgreSQL is down, tests that use the harness fail (not skip) with `docker compose up -d --wait db` in the message; tests that need no database still pass. The database is dropped even when a test fails; a killed process (`kill -9`) can leave a `wordwise_test_*` database behind, which you can drop by hand.

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
    assert client.get(f"/api/v1/profiles/{child_id}").json()["nickname"] == "Sam"
```

`test_harness.py` proves the harness: tables are empty at the start of every test, committed rows do not leak, and the failure behaviour above.

### Continuous integration

`.github/workflows/ci.yml` runs on every `pull_request` and on every push to `main`. One job, named `test` and shown on GitHub as `CI / test`, runs on `ubuntu-latest` with a PostgreSQL 18 service container (`postgres:18-alpine`, health-checked before the steps start) and `DATABASE_URL` pointing at it. It installs the backend (`uv sync --frozen`) and frontend (`bun install --frozen-lockfile`) dependencies, then runs `make test`: the backend pytest suite and the frontend suite. `make test` repeats the (no-op) installs and, because `CI=true` and the service database answers on 5432, does not call Docker or start a second database. Dependency downloads are cached, keyed on `backend/uv.lock` and `frontend/bun.lock`. Require the `CI / test` check before merging a pull request. On pushes to `main` a second job, `deploy`, runs after `test` passes and triggers the Render deploy hooks; see [`docs/deployment.md`](docs/deployment.md).
