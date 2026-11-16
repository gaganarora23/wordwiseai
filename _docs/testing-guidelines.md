# Testing guidelines

Draft. The strategy lives in `architecture.md` section 7; this file is the working rules.

## Run

- `make test` from the repo root installs dependencies, starts the database if needed, then runs the backend and frontend suites. It must pass before a PR.
- Backend alone: `cd backend && uv run pytest` (one file: `uv run pytest tests/test_x.py`).
- Frontend alone: `cd frontend && bun run test`.
- No setup step is needed on a fresh clone (Docker, uv and bun must be installed); `make test` installs from the lockfiles.

## Backend database harness

- Integration tests use real PostgreSQL. Locally it is the Compose service, started by `make test` when none is reachable (or `docker compose up -d --wait db`). In CI it will be a service container, configured in #47.
- The harness creates its own `wordwise_test_<random>` database on the server in `DATABASE_URL`, migrates it once per run and drops it at the end. The development database is never touched. The `DATABASE_URL` user needs `CREATEDB` (the Compose user and a CI service container have it). A killed process (`kill -9`) can leave a `wordwise_test_*` database behind.
- Fixtures in `backend/tests/conftest.py`: `clean_db` (Engine; the seven tables are truncated before and after each test), `db_session` (Session for your own inserts; commit to make rows visible to routes), `client` (`TestClient` with `get_session` overridden to the test database). Insert helpers: `insert_child`, `insert_word`, `insert_session_with_words` in `backend/tests/helpers.py`.
- Request `client` or `clean_db` explicitly; nothing is autouse, so tests that need no database still run when PostgreSQL is down.
- Example: `def test_x(client, db_session): insert_child(db_session); db_session.commit(); assert client.get(...).status_code == 200`.

## What to test

- Unit and integration tests only. No browser end-to-end suite in V0.
- Backend unit: pure logic in `services/` (mastery streak, review flag, word selection, hint scoring). No database.
- Backend integration: the API through FastAPI's `TestClient`, against real PostgreSQL, not SQLite.
- Frontend: component and routing tests with Vitest + Testing Library, mock-service rules, and `HttpService` against a mocked `fetch`.
- Cover the priority cases in `architecture.md` section 7.5 first.

## How to write them

- Every behavior change comes with a test in the same PR. A bug fix starts with a test that fails.
- Test behavior, not implementation: assert on what the user or API caller sees, not on internal calls.
- One behavior per test; name it for the behavior (`test_second_active_session_returns_409`).
- Tests are independent and order-free. Each starts from a clean state; no test relies on another's data.
- No network calls, real clocks, or randomness without a fixed seed or injected value.
- Do not mock what you own. Mock only external boundaries (`fetch`, time).
- Keep routes thin so logic is unit-testable without HTTP.

## Verifying `make test` itself

- It must exit non-zero if any backend or frontend test fails. When changing the Makefile, break one test in each suite, confirm a non-zero exit, then revert.
- Generated output (`node_modules`, `.output`, `dist`) stays ignored; `git status` is clean after a run.

## Out of scope for V0

Playwright, Schemathesis fuzzing, load testing.
