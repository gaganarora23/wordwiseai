# Testing guidelines

Draft. The strategy lives in `architecture.md` section 7; this file is the working rules.

## Run

- `make test` from the repo root runs the backend suite, then the frontend suite. It must pass before a PR.
- Backend alone: `cd backend && uv run pytest` (one file: `uv run pytest tests/test_x.py`).
- Frontend alone: `cd frontend && bun run test`.
- On a fresh clone run `cd frontend && bun install --frozen-lockfile` once. `make test` does not install.

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
