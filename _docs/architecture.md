# WordWise — Architecture and Tech Stack Decisions

**Status:** Agreed baseline for implementation
**Companion to:** `_docs/plan.md` (product specification v0.4)
**Scope of this document:** Backend, Frontend, Database, API, Testing, Deployment
([Section 8](#8-deployment)). Observability, alerting, and the on-call agent are
tabled (see [Section 8a](#8a-tabled-decisions)).

## 1. Guiding principles

1. **Simple and dependable over impressive.** V0 is a demo-scale app for a few
   child profiles. Avoid anything whose benefit only shows up at scale.
2. **The spec is the product authority.** `_docs/plan.md` fixes FastAPI,
   PostgreSQL, Docker Compose, a Lovable-generated frontend, OpenAPI 3.1, and a
   monorepo. This document only decides what the spec leaves open.
3. **One contract, mechanically enforced.** Frontend and backend must not drift
   apart; a CI check, not discipline, prevents it.
4. **Target of 17 rubric points** (see [Section 9](#9-course-rubric-mapping)).
   Choices that do not move a rubric point or a spec requirement are cut.

## 2. System overview

```
Browser
  │  TanStack Router + TanStack Query (React 19, Tailwind v4, shadcn/Radix)
  │  service layer: mockService | HttpService  (selected by env flag)
  ▼
FastAPI  (/api/v1, /docs)
  │  api (routes) → services (business rules) → models (SQLAlchemy)
  │  Pydantic v2 request/response schemas
  ▼
PostgreSQL  (schema managed by Alembic, persistent Docker volume)
```

Three separately buildable services in one monorepo (spec §5.5):
`frontend/`, `backend/`, and PostgreSQL, orchestrated by one
`docker-compose.yml`.

## 2a. Versions

Versions below were checked on 2026-11-14 (PyPI, npm, Docker Hub, and a real
`uv` dependency resolution). Pin them in `pyproject.toml` / `uv.lock`,
`package.json` / `bun.lock`, the Dockerfiles, and Compose. Update this table
whenever a pin changes.

### Backend and runtime

| Technology | Version | Notes |
|---|---|---|
| Python | **3.13** | Managed by `uv` via `.python-version`; the macOS system Python (3.9) is not used. Every library below supports it. |
| uv | 0.13 (installed locally) | Used for install, run, and lockfile |
| FastAPI | 0.163 | Requires Python 3.11+ |
| Starlette | 1.10 | Pulled in by FastAPI; do not pin separately |
| Uvicorn | 0.54 | ASGI server |
| SQLAlchemy | 2.1 | Sync API; requires Python 3.11+ |
| Alembic | 1.20 | Migrations |
| Pydantic | 2.14 | v2 |
| pydantic-settings | 2.16 | Environment-based configuration |
| psycopg | 3.3 (`psycopg[binary]`) | Driver, URL scheme `postgresql+psycopg://` |
| pytest | 9.2 | Dev dependency |
| httpx | 0.28 | Dev dependency; required by FastAPI's `TestClient` |
| PostgreSQL | **18** (`postgres:18-alpine`) | Same major version locally, in CI, and when deployed |

### Frontend (versions already in the imported project; do not upgrade casually)

| Technology | Version | Notes |
|---|---|---|
| Node | 24 LTS | Matches the locally installed Node; use the same major in the Dockerfile and CI |
| bun | 1.4 | Package manager; keeps the imported `bun.lock`. Must be installed locally. |
| React | 19.2 | |
| TypeScript | 5.8 | |
| Vite | 8.1.5 | Exact pin in the imported project |
| TanStack Start / Router | 1.168.60 / 1.170.41 | **Exact pins** in the imported project; keep them unless a task upgrades them deliberately |
| TanStack Query | 5.101 | |
| Tailwind CSS | 4.2 | |
| Vitest | 4.1 | |
| `openapi-typescript` | latest at install time | Added in task 34; record the resolved version here |

### Compatibility checks

- **Backend resolution:** a trial `uv add` of the full backend set on Python 3.13
  resolved cleanly with no conflicts (the versions above are the resolved ones).
- **Verified at runtime (task 6):** SQLAlchemy 2.1 + psycopg 3.3 + Alembic 1.20
  work together against PostgreSQL 18 (connect, migrate up/down, constraints,
  `alembic check`). No version had to be pinned back.
- **Frontend:** versions are the ones Lovable generated and tested together.
  Treat them as a unit; changing one TanStack package alone can break the build.
- **Frontend engine requirements** (Node range for Vite 8) were not confirmed
  from package metadata. Confirm during task 2 by running the build and tests on
  Node 24.
- **Cross-stack:** Python and Node versions do not interact; the only coupling is
  `openapi.yaml`, enforced by the CI drift check.

## 3. Backend

### 3.1 Stack

| Concern | Choice |
|---|---|
| Language / framework | Python, FastAPI |
| ORM | SQLAlchemy 2.x, **synchronous** |
| Migrations | Alembic |
| Validation / schemas | Pydantic v2 |
| DB driver | psycopg 3 (`postgresql+psycopg://`) |
| Tests | pytest + FastAPI `TestClient` |

### 3.2 What each library does

- **Pydantic v2** defines the API shape. It validates requests (nickname 1–20
  characters, daily goal 5 or 10, `extra="forbid"` to match
  `additionalProperties: false`) and defines response models. FastAPI uses
  these to produce the OpenAPI schema. It never touches the database.
- **SQLAlchemy 2.x** maps tables to Python classes, expresses constraints
  (partial unique index, `UNIQUE(session_id, word_id)`), builds queries such as
  the deterministic daily word selection, and owns transactions.
- **psycopg 3** is the PostgreSQL driver SQLAlchemy uses. It is configured once
  in the connection URL.
- **Alembic** versions the schema. `alembic upgrade head` builds the schema on a
  fresh database, which supports one-command startup.

### 3.3 Why synchronous SQLAlchemy

Async only pays off under many concurrent waiting requests. A demo app does not
need that, and async adds lazy-loading pitfalls and harder test setup. FastAPI
runs sync routes in a thread pool, so concurrency is still adequate. The most
important rule in the spec, committing mastery and review changes in one
transaction at session completion, is easiest to reason about synchronously.

### 3.4 Layering

```
backend/app/
├── api/        # FastAPI routers: parse request, call a service, return a response model
├── schemas/    # Pydantic request/response models (the API contract)
├── models/     # SQLAlchemy ORM models (the database shape)
├── services/   # Business rules; no HTTP and no FastAPI imports
└── main.py
```

- Keep **routes thin**. Rules live in `services/` so they can be unit-tested
  without HTTP or a database.
- Keep **Pydantic schemas and ORM models separate**. Some field duplication is
  deliberate: the database shape and the API contract are allowed to differ.
- Business rules that must live in services:
  - deterministic daily word selection (spec §7.3)
  - session lifecycle and sequential learning-card progression (spec §7.4)
  - answer submission and automatic completion on the final answer (spec §8–9)
  - mastery and review commit at completion (spec §9.2–9.3)
  - dashboard aggregations (spec §10.1)

### 3.5 Transaction rule (most important)

When the final unanswered word is submitted, the backend must, **in a single
database transaction**: record the answer, mark the session `completed`, write
the `quizResults` row, and apply every mastery and review update. If any step
fails, nothing is committed. Answers in unfinished or abandoned sessions never
change committed mastery or the review pool.

### 3.6 Vocabulary ingestion

- Source: one JSON file per grade under `backend/data/`.
- A Python script validates (required fields, grade, stable IDs, syllables,
  exactly four options with exactly one correct) and upserts into PostgreSQL.
- Idempotent: rerunning creates no duplicates. It reports per-grade counts and
  validation failures. The expected release total is 650 words; development
  fixtures need at least 10 words per grade.

### 3.7 Dependencies and tooling

- Use **`uv`** with `pyproject.toml` and a committed `uv.lock` for dependency
  management, replacing the `requirements.txt` shown in the spec's layout (the
  spec treats folder names as flexible). Run tools via `uv run` (e.g.
  `uv run pytest`) and install with `uv sync`. The backend Dockerfile installs
  from the lockfile (`uv sync --frozen`).
- Configuration via environment variables (database URL, CORS origins).

## 4. Database

### 4.1 Engine and operations

- PostgreSQL, run as a Docker Compose service with a **named persistent
  volume** so data survives container restarts.
- Schema owned by **Alembic migrations** (kept under `backend/`, with
  `database/` for any raw SQL or setup assets). No manual schema edits.
- Tests run against **real PostgreSQL**, not SQLite, because the partial unique
  index and transactional behavior must be exercised.

### 4.2 Entities (from spec §5.3)

| Table | Key points |
|---|---|
| `children` | UUID PK, nickname, grade, daily_goal, created_at, updated_at |
| `words` (vocabulary) | UUID PK, word, grade, definition, example, syllables, content version; plus the four prewritten options with exactly one correct, and an explanation |
| `sessions` | UUID PK, child FK, mode (`daily`/`review`), phase (`learning`/`quiz`), status (`in_progress`/`completed`/`abandoned`), current_position (zero-based), timestamps |
| `session_words` | session FK, word FK, display order; `UNIQUE(session_id, word_id)` |
| `answers` | session FK, word FK, selected option, correctness, hint_used, answered_at; one answer per word per session |
| `quiz_results` | session FK, score, correct/incorrect counts, review-word IDs |
| `word_mastery` | child FK, word FK, status, consecutive_correct, last_practiced, needs_review flag |

Use stable UUIDs for profiles, words, questions, and sessions. Never use display
text as an identifier.

### 4.3 Constraints that must live in PostgreSQL

These are required by the spec and must not rely on application logic alone:

1. **One unfinished session per profile:** a **partial unique index** on
   `sessions(child_id) WHERE status = 'in_progress'`.
2. **A word appears at most once per session:** `UNIQUE(session_id, word_id)`.
3. **One immutable answer per word per session:** unique on
   `(session_id, word_id)` in `answers`.
4. **Profile deletion removes all learning history:** foreign keys with
   `ON DELETE CASCADE` from children to sessions, answers, results, and mastery.

### 4.4 Modeling notes

- `NEEDS_REVIEW` is a **flag** on `word_mastery`, separate from the
  `NEW`/`LEARNING`/`MASTERED` status. Keep quiz correctness, mastery progress,
  and review status as separate dimensions (spec §9.4).
- Mastery is keyed to stable word IDs and grade. Changing a child's grade
  abandons the active session but **keeps** existing mastery data; it is not
  erased.
- Dashboard data is derived from these persisted tables only; the frontend
  never estimates progress.

## 5. API

### 5.1 Contract workflow (decision)

**Generated from FastAPI stubs; the exported file is committed.**

1. Write Pydantic schemas and route **stubs** (signatures and response models, no
   logic) for every endpoint in spec §14.
2. A script exports FastAPI's schema to **`openapi.yaml` at the repository
   root**, and the file is committed.
3. The frontend builds against that file (generated types plus the mock service)
   while backend logic is still being written.
4. **CI re-exports the schema and fails if it differs from the committed file.**
   This drift check is what makes the committed file trustworthy.

Rationale: nobody hand-maintains YAML, the file cannot silently go stale, and the
contract still exists before the logic does. Trade-off: the code is technically
the source of truth, and the committed file is a verified snapshot. Schemathesis
was considered and **dropped** as over-engineering for V0.

### 5.2 Conventions (from spec §14.2)

- Versioned under `/api/v1`; JSON bodies; UUID identifiers; ISO 8601 timestamps;
  snake_case field names.
- `404` missing resource, `409` state conflict, `422` validation failure.
- `/docs` exposes interactive documentation.

### 5.3 Endpoints (spec §14.3)

`GET /health`; profiles CRUD (`/profiles`, `/profiles/{id}`);
`GET /grades/{grade}/words`; `GET /profiles/{id}/sessions/active`;
`POST /sessions`; `GET /sessions/{id}`; `PATCH /sessions/{id}/progress`;
`POST /sessions/{id}/answers`; `POST /sessions/{id}/abandon`;
`GET /sessions/{id}/results`; `GET /profiles/{id}/progress`.
Dashboard endpoints (7/30-day metrics, review list, session history) are added
during dashboard implementation and reflected in `openapi.yaml` before frontend
integration (spec §13.1).

### 5.4 Details that need explicit FastAPI annotation

These are easy to get wrong in generated schemas, so the stubs must set them
deliberately and the exported file must be reviewed for each:

- `GET .../sessions/active` returns **`200` with a session or `204` with no
  body**.
- `POST /sessions` request is a **`oneOf`** (discriminated union) of the daily
  and review request schemas; review requires 1–10 unique `review_word_ids`.
- `409` responses carry structured bodies: `active_session_id` when a session
  already exists, and available/requested counts for `INSUFFICIENT_WORDS`.
- `Profile` is a **single flattened object** (`id`, `nickname`, `grade`,
  `daily_goal`, `created_at`, `updated_at`), not `allOf` over a strict create
  schema.
- Answer submission takes `word_id`, `selected_option_id`, `hint_used`. The
  **backend determines correctness**; the client never sends it.
- The final answer **automatically completes** the session; there is no separate
  completion endpoint.

### 5.5 Cross-origin access

The browser calls FastAPI directly. Configure CORS via an environment variable,
or route through a reverse-proxy path in Docker Compose. The exact choice is
made when the Compose file is written.

## 6. Frontend

### 6.1 Starting point: reuse the existing Lovable project

The frontend is copied from `grade-five-word-garden` into `frontend/`. That
repository is **read-only to us**: files are copied out, and nothing is pushed
to it. After the copy, the monorepo is the only place the UI is edited.

What the project already uses (verified by inspection):

| Area | Existing |
|---|---|
| Framework | TanStack Start (SSR, Vite 8, Nitro), React 19, TypeScript |
| Routing | TanStack Router (file-based) — not React Router |
| Server state | TanStack Query, already wired in `__root.tsx` and `routes/index.tsx` |
| UI | Tailwind v4, shadcn/Radix components, lucide-react, sonner |
| Forms / validation | react-hook-form + Zod |
| Tests | Vitest + Testing Library (routing and mock-service tests exist) |
| Package manager | bun |
| Existing screens | Profile picker, profile create/edit/delete dialogs, learn route |

### 6.2 What to copy and what to leave behind

- **Copy:** `src/`, config files, `package.json`, lockfile, `components.json`.
- **Leave out:** the `.git` history, `.lovable/` metadata, and the
  Lovable-specific block in its `AGENTS.md`.
- Consequence: Lovable can no longer push into this repository. UI changes are
  made in code from here on.

### 6.3 The service seam (core integration point)

All screens call a `WordWiseService` interface in `src/services/types.ts`.
`src/services/index.ts` exports `service`, currently a localStorage mock.
Existing guidance in the project's `AGENTS.md` already says to keep selection
and persistence behind this boundary.

**Plan:**

1. Rebuild the types in `services/types.ts` from types **generated out of
   `openapi.yaml`** (`openapi-typescript`).
2. Write an **`HttpService`** that implements the updated interface using a small
   typed `fetch` wrapper.
3. Keep the **mock service as the mock mode** (no MSW). Because it implements the
   same generated types, it conforms to the contract at compile time.
4. Select the implementation with one env flag, e.g. `VITE_USE_MOCK`.

### 6.4 The existing interface predates spec v0.4 and must be updated

| Existing mock/interface | Spec v0.4 requirement |
|---|---|
| camelCase (`dailyGoal`, `childId`) | snake_case (`daily_goal`, `profile_id`) |
| Phases `learn` / `quiz` / `done` | `phase`: `learning` / `quiz`; `status`: `in_progress` / `completed` / `abandoned` |
| `startOrResumeSession` (single call) | `GET .../sessions/active` (200/204) then `POST /sessions` (409 on conflict) |
| `submitAnswer` by index; client sends correctness | By `word_id`; backend decides correctness |
| `completeSession()` call | Automatic on the final answer |
| Words may repeat to fill the goal | No repeats; `409 INSUFFICIENT_WORDS` |
| Simple mock selection | Deterministic priority and tie-break rules (spec §7.3) |
| No abandon, no dashboard | Both required |
| Mock persistence comment mentions IndexedDB | Real persistence is PostgreSQL via the API |

The mock service must be reworked to follow the same rules so mock and real
behavior match (spec §7.3: "deterministic so mock and backend behavior match").

### 6.5 State and routing

- **TanStack Query** for all server state: loading and error states, retries,
  refetch after answers. This supports the spec's requirement to show clear
  errors and never claim unsaved progress was saved.
- **TanStack Router** for screens: profile picker, learning, quiz, results,
  parent dashboard.
- On profile select, call `GET .../sessions/active` and resume the returned
  session; do not reshuffle on restore.

### 6.6 Known frontend risks

1. **SSR build target.** TanStack Start with Nitro defaults to a Cloudflare
   build. The Compose frontend container needs a Node server preset (or a
   client-only build). Resolve when writing the frontend Dockerfile.
2. **Responsive requirements** (spec §12.1) apply to every screen including the
   dashboard; validate at desktop, tablet, and a narrow phone viewport.
3. **Accessibility:** feedback must not rely on colour alone; large touch
   targets; keyboard-accessible controls.

## 7. Testing

### 7.1 Principle

The rubric asks for **unit and integration tests that run with a single command
and pass**. Cover that fully and stop. No end-to-end browser suite in V0.

### 7.2 Layers

| Layer | Scope | Tools | Database |
|---|---|---|---|
| Backend unit | Pure service logic: mastery streak, review-flag set/clear, daily word selection and tie-breaks, hint scoring | pytest | None |
| Backend integration | API through `TestClient`: session lifecycle (create → progress → answers → auto-complete → results), one-active-session `409`, `INSUFFICIENT_WORDS` `409`, immutable answers, profile delete cascade, grade-change abandon, dashboard aggregates | pytest + `TestClient` | **Real PostgreSQL** |
| Frontend | Component and routing tests; `HttpService` behavior against mocked `fetch`; mock service rules | Vitest + Testing Library | None |
| Contract | CI check that the exported schema matches the committed `openapi.yaml` | script | None |

### 7.3 Database in tests

- Locally, PostgreSQL runs as a Compose service.
- In CI, it runs as a service container.
- Each test run starts from migrated schema (`alembic upgrade head`) and cleans
  state between tests. No testcontainers dependency.

### 7.4 Single command

A root `Makefile` target, **`make test`**, runs backend and frontend suites.
`make up` (or `docker compose up`) starts the full stack.

### 7.5 Priority test cases (derived from the acceptance checklist)

- Three consecutive correct answers across three **separate completed**
  sessions → `MASTERED`; daily and review sessions both count.
- Incorrect answer resets the streak and sets the review flag; hinted-correct
  counts as correct and sets the review flag.
- Review flag clears only on a correct, unhinted answer in a **completed**
  session; abandoned or unfinished sessions change nothing.
- Daily session has exactly 5 or 10 distinct words; shortage returns `409`
  without creating a partial session.
- Partial unique index rejects a second `in_progress` session.
- Learning progress can only advance one card at a time; quiz transition only
  after the final card.
- Restoring a session preserves word order and previously submitted answers.
- Dashboard accuracy uses submitted answers from completed sessions only.

### 7.6 Explicitly out of scope for V0 testing

Playwright end-to-end tests, Schemathesis fuzzing, load/performance testing.

## 8. Deployment

**Provider: Render (free tier).** Chosen because it needs no payment card, a
Blueprint (`render.yaml` at the repo root) creates the database and both web
services from our existing Dockerfiles in one step, and its deploy hooks fit our
CI gate (tests must pass before anything deploys). Alternatives considered:
Fly.io (needs a card and CLI authentication) and Railway (needs a card or a
trial).

**Topology** (all on free plans, defined in `render.yaml`):

- `wordwise-db`: managed PostgreSQL. Major version **18** on the free plan
  (owner-reported from the Render dashboard on 2026-11-16), the same major as
  local and CI. Render's connection string starts with `postgresql://`;
  `backend/app/config.py` rewrites it (and `postgres://`) to
  `postgresql+psycopg://`, so the app and Alembic use the same URL path.
- `wordwise-api`: Docker web service from `backend/Dockerfile`, listening on
  port 8000. Public URL `https://wordwise-api-xji2.onrender.com` (Render
  appended the suffix because the plain name was taken).
- `wordwise-web`: Docker web service from `frontend/Dockerfile`, listening on
  port 8080. Public URL `https://wordwise-web.onrender.com`.
- The browser calls the API directly; CORS on the API is limited to the web
  origin (`CORS_ORIGINS`). The API URL is baked into the frontend at build time
  through `VITE_API_URL`, so if the API URL changes the frontend must be
  rebuilt.

**How deploys happen.** Auto-deploy is off for both web services. After the
`test` job passes on a merge to `main`, the GitHub Actions `deploy` job
(`needs: test`) calls the two Render deploy hooks (secrets in GitHub). Details,
setup and rollback: [`docs/deployment.md`](../docs/deployment.md). On start the
backend runs migrations and idempotent vocabulary ingestion.

**Known limits.** Free web services sleep after idle, so the first request
takes about a minute. The free PostgreSQL database expires after 30 days. The
deployment is a shared demo with no authentication, so real children's data
must not be entered.

## 8a. Tabled decisions

These are deliberately deferred and not part of the current target:

- **CI/CD pipeline details** beyond: run tests on pull requests, check
  OpenAPI drift, and deploy automatically on merge.
- **Observability** (metrics, traces, structured logs sharing a trace ID, a
  viewing UI).
- **Alerting** (including the optional uptime alert).
- **On-call responder agent.**

## 9. Course rubric mapping

Target: **17 of 24 points** (pass threshold is 10). Peer review of three other
projects is mandatory in addition.

| Criterion | Max | Planned | Notes |
|---|---|---|---|
| Problem description | 2 | 2 | README: problem, functionality, expected behavior |
| Product specification | 2 | 2 | Spec exists; add a **public tracker** (GitHub Issues/Projects) seeded from the §16 checklist, worked via PRs |
| Agent team specification | 2 | 2 | `docs/agents.md`: roles and hand-offs |
| Context management | 2 | 2 | `AGENTS.md` linking to modular docs |
| Application | 2 | 2 | End to end, one command |
| Testing | 2 | 2 | Unit + integration, `make test` |
| Containerization | 2 | 2 | Compose: frontend, backend, Postgres |
| Deployment | 2 | 2 | Public URL |
| CI/CD | 3 | 2 | Tests on PR plus automatic deploy; skip the dev/manual-prod split |
| Observability | 2 | 0 | Tabled |
| Alerting | 1 | 0 | Tabled |
| On-call agent | 2 | 0 | Tabled |
| **Total** | **24** | **18 possible / 17 target** | One point of buffer above target |

## 10. Decisions summary

| # | Area | Decision |
|---|---|---|
| 1 | Backend data layer | SQLAlchemy 2 (sync) + Alembic + Pydantic v2 + psycopg 3 |
| 2 | Contract | FastAPI stubs export `openapi.yaml`; CI fails on drift; no Schemathesis |
| 3 | Frontend | Copy Lovable project into `frontend/`; TanStack Router + Query; mock service is mock mode; `openapi-typescript` + `HttpService`; original repo untouched |
| 4 | Testing | pytest unit + integration on real Postgres; Vitest frontend; `make test`; no Playwright |
