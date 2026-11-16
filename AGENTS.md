# WordWise

Child-friendly vocabulary-learning web app (Kindergarten to Grade 12): a FastAPI backend, a React frontend and PostgreSQL. This repository is a monorepo built for the DataTalks.Club AI Dev Tools course final project.

## Layout

- `backend/` - FastAPI, SQLAlchemy, Alembic, pytest (uv). See `backend/AGENTS.md`.
- `frontend/` - React (Vite, TanStack), Vitest (bun). See `frontend/AGENTS.md`.
- `docker-compose.yml` - PostgreSQL, backend and frontend containers.
- `Makefile` - `make test` installs dependencies, starts the database if needed and runs both test suites.
- `.github/workflows/ci.yml` - CI (`CI / test`) on pull requests and pushes to `main`.
- `_docs/` - specification, architecture, tasks, process, role instructions and testing guidelines (below).
- `docs/` - agent team and working conventions: `docs/agents.md`, `docs/process.md`.

## Documents

Read the one that matches your task before starting:

- `_docs/plan.md` - product specification: goals, non-goals, behavior, data model, API contract.
- `_docs/architecture.md` - tech choices, versions, layout, conventions.
- `_docs/tasks.md` - the task backlog; each task is also a GitHub issue with acceptance criteria.
- `_docs/api.md` - where the API contract lives (live OpenAPI) and its conventions.
- `_docs/design-system.md` - frontend styling tokens and components, as built.
- `docs/agents.md` - the agent roles, what each must not do, who owns an issue at each stage.
- `docs/process.md` - branches, pull requests, CI and merge conventions.
- `_docs/process.md` - how work is organized: orchestrator, lifecycle, labels, rules.
- `_docs/task-template.md` - the format a groomed task must follow.
- `_docs/testing-guidelines.md` - read before writing tests.
- `_docs/team/pm.md`, `_docs/team/software-engineer.md`, `_docs/team/qa-engineer.md` - the role instructions each subagent follows.
- `README.md` - how to run, test and configure the project.

## Commands

Prerequisites: `uv`, `bun` and Docker installed (`make test` runs the installs and starts the database itself).

- `docker compose up --build` - run the full stack (PostgreSQL, API on `:8000`, UI on `:8080`).
- `docker compose up -d --wait db` - start only PostgreSQL.
- `make test` - installs dependencies, starts the database if none is reachable, then runs the backend (pytest) and frontend (Vitest) suites; non-zero if either fails. Never overrides a configured `DATABASE_URL`; see README Testing.
- `cd backend && uv run uvicorn app.main:app` - run the API alone.
- `cd frontend && bun run dev` - run the UI alone.
- API contract: FastAPI generates the OpenAPI document at `http://localhost:8000/openapi.json` (docs at `/docs`). A committed `openapi.yaml`, an export script and generated frontend types are planned (`_docs/architecture.md`) but not built, so there is no regenerate command yet. See `_docs/api.md`.

## Rules

- No accounts: registration, login and authentication are out of scope.
- `_docs/plan.md` is the source of truth for behavior and the API; if code disagrees, raise it, do not silently diverge.
- The original Lovable repository (`grade-five-word-garden`) is never modified; `frontend/` is a copy.
- Work comes from GitHub issues, one at a time. Read the acceptance criteria before starting and before closing.
- Follow the lifecycle in `_docs/process.md` (PM grooms, engineer implements, QA verifies) and the branch, PR and CI conventions in `docs/process.md`.
- Do not add a dependency without asking.
- Keep `README.md` accurate as decisions finalize; reviewers read it first.
