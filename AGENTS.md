# WordWise

Child-friendly vocabulary-learning web app (Kindergarten to Grade 12): a FastAPI backend, a React frontend and PostgreSQL. This repository is a monorepo built for the DataTalks.Club AI Dev Tools course final project.

## Layout

- `backend/` - FastAPI, SQLAlchemy, Alembic, pytest (uv). See `backend/AGENTS.md`.
- `frontend/` - React (Vite, TanStack), Vitest (bun). See `frontend/AGENTS.md`.
- `docker-compose.yml` - PostgreSQL (and, as tasks land, the app containers).
- `_docs/` - specification, architecture and process documents (below).

## Documents

Read the one that matches your task before starting:

- `_docs/plan.md` - product specification: goals, non-goals, behavior, data model, API contract.
- `_docs/architecture.md` - tech choices, versions, layout, conventions.
- `_docs/tasks.md` - the task backlog; each task is also a GitHub issue with acceptance criteria.
- `_docs/process.md` - how work is organized: orchestrator, lifecycle, labels, rules.
- `_docs/task-template.md` - the format a groomed task must follow.
- `_docs/testing-guidelines.md` - read before writing tests.
- `_docs/team/pm.md`, `_docs/team/software-engineer.md`, `_docs/team/qa-engineer.md` - the role instructions each subagent follows.
- `README.md` - how to run, test and configure the project.

## Commands

- `make test` - backend and frontend suites (needs `docker compose up -d --wait db`).
- `docker compose up -d --wait db` - start PostgreSQL.
- `cd backend && uv run uvicorn app.main:app` - run the API.
- `cd frontend && bun run dev` - run the UI.

## Rules

- Work comes from GitHub issues, one at a time. Read the acceptance criteria before starting and before closing.
- Follow the lifecycle in `_docs/process.md`: PM grooms, engineer implements, QA verifies.
- Do not add a dependency without asking.
- Keep `README.md` accurate as decisions finalize; reviewers read it first.
