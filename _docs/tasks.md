# WordWise — Task Backlog

Each task is sized for one session. Descriptions are written so a task can be
picked up without reading the others; where a task needs earlier work to exist,
the description says so. Product behavior is defined in `_docs/plan.md` (the
spec) and tech choices in `_docs/architecture.md`.

## 1. Empty project with a passing test
Goal: A fresh monorepo with a backend project whose single test passes via `make test`.
Description: Create the repository skeleton from the spec's layout (`backend/`, `frontend/`, `docs/`, root `Makefile`). Initialize `backend/` as a `uv` project pinned to Python 3.13 (`.python-version`, `pyproject.toml`, `uv.lock`) with pytest and one trivial passing test; versions are listed in `_docs/architecture.md` section 2a. Add a root `make test` target that runs it.

## 2. Import the Lovable frontend with passing tests
Goal: The existing frontend lives in `frontend/` and its Vitest suite passes.
Description: Copy the source, config, `package.json`, and lockfile from the `grade-five-word-garden` repository into `frontend/`, leaving out its `.git` history, `.lovable/` metadata, and the Lovable-specific block in its `AGENTS.md`. Do not modify or push to the original repository. Install bun 1.4 if it is missing (it is not installed on the author's machine) and use Node 24, then install dependencies, confirm `bun run test` and `bun run build` pass, and extend `make test` to run the frontend suite too.

## 3. FastAPI app with a health endpoint
Goal: A running FastAPI app that serves `GET /api/v1/health` and `/docs`.
Description: Create the app entry point (`backend/app/main.py`) with the `api/`, `schemas/`, `models/`, and `services/` package layout. Add the health route under the `/api/v1` prefix with a typed response model, and a test that calls it through FastAPI's `TestClient`.

## 4. PostgreSQL in Docker Compose with a persistent volume
Goal: `docker compose up db` starts PostgreSQL and data survives a restart.
Description: Add a root `docker-compose.yml` with a PostgreSQL 18 service (`postgres:18-alpine`), a named volume, a healthcheck, and credentials taken from environment variables with a documented `.env.example`. Verify that a row written before `docker compose restart` is still present afterwards.

## 5. Database configuration and session management
Goal: The backend reads its database URL from the environment and can open SQLAlchemy sessions.
Description: Add a settings module (database URL, allowed CORS origins) driven by environment variables, a SQLAlchemy 2.x synchronous engine using the `postgresql+psycopg://` driver, and a FastAPI dependency that yields one session per request. Include a test that confirms a trivial query succeeds against a running PostgreSQL.

## 6. Alembic setup and the children and words tables
Goal: `alembic upgrade head` creates the `children` and `words` tables.
Description: Configure Alembic against the backend's SQLAlchemy models and write the first migration. `children` has a UUID primary key, nickname, grade, daily goal, and timestamps; `words` holds the vocabulary fields from spec section 6.2 plus four answer options with exactly one correct and an explanation. Add a downgrade path.

## 7. Migration for sessions, session words, and answers
Goal: The session-related tables exist with the constraints the spec requires.
Description: Add a migration for `sessions` (mode, phase, status, zero-based current position, timestamps), `session_words`, and `answers`, with foreign keys that cascade on child deletion. Enforce in PostgreSQL a partial unique index allowing one `in_progress` session per child, and unique `(session_id, word_id)` in both `session_words` and `answers`. Write tests that prove each constraint rejects a violating insert.

## 8. Migration for quiz results and word mastery
Goal: The `quiz_results` and `word_mastery` tables exist.
Description: Add a migration for `quiz_results` (score, correct/incorrect counts, review-word IDs per session) and `word_mastery` (child, word, status of `NEW`/`LEARNING`/`MASTERED`, consecutive-correct count, last-practiced timestamp, and a separate `needs_review` flag). Foreign keys cascade on child deletion, and one mastery row exists per child and word.

## 9. Backend integration test harness on real PostgreSQL
Goal: pytest fixtures give every integration test a migrated, clean PostgreSQL database.
Description: Add shared fixtures that connect to the test database, run `alembic upgrade head` once per run, and clean data between tests, plus a `TestClient` fixture wired to that database. Document how the database is provided locally (the Compose service) and in CI (a service container). Include one example integration test.

## 10. Vocabulary file format and validator
Goal: A function that validates a grade's vocabulary JSON and reports every problem.
Description: Define the per-grade JSON format (stable word ID, word, grade, definition, example sentence, syllables, content version, and a question with four options, exactly one correct, plus an explanation). Implement a validator that checks required fields, grade match, ID stability and uniqueness, syllable data, and the four-options/one-correct rule, returning all failures rather than the first. Cover it with unit tests.

## 11. Idempotent vocabulary ingestion script
Goal: One command loads all grade files into PostgreSQL without creating duplicates.
Description: Write a Python script run with `uv run` that validates the files in `backend/data/`, then inserts or updates words by stable ID. It prints per-grade counts and validation failures, exits non-zero on failure, and reports the expected 650 total only when it is reached. Test that running it twice leaves the same row count.

## 12. Development fixture vocabulary
Goal: At least 10 distinct words for every grade from Kindergarten through Grade 12.
Description: Write clearly marked development fixture JSON files (separate from release content) covering all 13 grades, each with at least 10 words so both the 5- and 10-word daily goals can be exercised. Every entry must pass the validator and load through the ingestion script. These are not release content and must not be presented as such.

## 13. Release vocabulary: Kindergarten to Grade 3
Goal: 50 curated, age-appropriate words per grade for K, 1, 2, and 3 (200 words).
Description: Write grade JSON files in the validated format, with student-friendly definitions, example sentences, syllable breakdowns like `ba · na · na`, and four-option questions with short encouraging explanations. Distractor options must be plausible but clearly wrong. All entries must pass the validator.

## 14. Release vocabulary: Grades 4 to 6
Goal: 50 curated, age-appropriate words per grade for Grades 4, 5, and 6 (150 words).
Description: Same format and quality bar as the other release content tasks. Choose words appropriate to each grade's level, avoid duplicating words across grades, and ensure all entries pass the validator.

## 15. Release vocabulary: Grades 7 to 9
Goal: 50 curated, age-appropriate words per grade for Grades 7, 8, and 9 (150 words).
Description: Same format and quality bar as the other release content tasks. Choose words appropriate to each grade's level, avoid duplicating words across grades, and ensure all entries pass the validator.

## 16. Release vocabulary: Grades 10 to 12
Goal: 50 curated, age-appropriate words per grade for Grades 10, 11, and 12 (150 words).
Description: Same format and quality bar as the other release content tasks. Once this and the other release content tasks are done, the ingestion script should report 650 words total with no validation failures.

## 17. Profile schemas and create/list/get endpoints
Goal: Parents can create a profile and list or fetch profiles through the API.
Description: Add Pydantic schemas (`ProfileCreate` with nickname 1 to 20 characters, grade K to 12, daily goal 5 or 10, and extra fields forbidden; a single flattened `Profile` response with ID and timestamps) and the endpoints `POST /api/v1/profiles`, `GET /api/v1/profiles`, and `GET /api/v1/profiles/{profile_id}`. Return `404` for unknown IDs and `422` for invalid input, with integration tests.

## 18. Profile update and delete endpoints
Goal: Parents can change a profile's nickname, grade, and goal, or delete the profile permanently.
Description: Add `PUT` and `DELETE` on `/api/v1/profiles/{profile_id}`. Deletion removes the profile and, through foreign-key cascades, all associated sessions, answers, results, and mastery rows; it is permanent. Test that a deleted profile's related rows are gone and that invalid updates return `422`.

## 19. Grade vocabulary endpoint
Goal: The API returns the curated words for one grade.
Description: Add `GET /api/v1/grades/{grade}/words`, returning the words for that grade only, with their question options (the spec allows `is_correct` on options for the demo). Reject unknown grades with `422`. Test using the development fixture content.

## 20. Daily word selection logic
Goal: A pure function that picks a child's daily words using the spec's deterministic rules.
Description: Implement selection per spec section 7.3: prefer words flagged `NEEDS_REVIEW`, then `LEARNING`, then `NEW`, then `MASTERED`; within a group, least-recently-practiced first with never-practiced first; ties broken by stable word ID ascending; each word at most once. If fewer words exist than requested, raise a typed insufficient-words error carrying the available and requested counts. Unit-test every rule without a database.

## 21. Mastery and review rules logic
Goal: A pure function that computes mastery and review changes from a completed session's answers.
Description: Implement spec section 9: a correct answer increments the consecutive-correct streak, an incorrect answer resets it to zero, three consecutive corrects across separate completed sessions yield `MASTERED`, and a hinted-correct answer counts as correct but also sets `needs_review`. A correct unhinted answer clears the review flag. Unit-test each rule without a database.

## 22. Create daily session endpoint
Goal: `POST /api/v1/sessions` creates a daily session with a fixed word order.
Description: Accept a daily request (profile ID, optional word count of 5 or 10 defaulting to the profile's goal), select words with the daily selection logic, and persist the session and its ordered words in `learning` phase at position zero. Return `409` with `active_session_id` if the child already has an in-progress session, and `409 INSUFFICIENT_WORDS` with available and requested counts without creating anything. Integration-test both conflicts.

## 23. Create review session endpoint
Goal: `POST /api/v1/sessions` also creates a targeted review session.
Description: Accept a review request (profile ID and 1 to 10 unique `review_word_ids`) as a separate `oneOf` schema from the daily request. Reject duplicate, unknown, wrong-grade, or non-review words with a validation error rather than substituting words. Review sessions may contain fewer than five words; test valid and invalid lists.

## 24. Get session and active session endpoints
Goal: A client can resume an unfinished session after a browser refresh.
Description: Add `GET /api/v1/sessions/{session_id}` and `GET /api/v1/profiles/{profile_id}/sessions/active`, the latter returning `200` with the session or `204` with no body. The response includes fixed word order, phase, position, and previously submitted answers with feedback (explanation and correct option) so the UI can restore state without reshuffling. Test that two reads return the same order.

## 25. Session progress endpoint for the learning phase
Goal: The server records learning-card progress and gates the move to the quiz.
Description: Add `PATCH /api/v1/sessions/{session_id}/progress` accepting phase and zero-based position. Learning position may advance only one card at a time, cannot jump ahead, and the transition to `quiz` at position zero is accepted only after position reaches the word count. Invalid moves return `409`; test each rule.

## 26. Submit answer endpoint
Goal: A child can submit one immutable answer for the next unanswered word.
Description: Add `POST /api/v1/sessions/{session_id}/answers` taking `word_id`, `selected_option_id`, and `hint_used`. The backend decides correctness, accepts only the next unanswered word in quiz order, advances the position, and returns correctness with the explanation. Duplicate, out-of-order, or learning-phase submissions return `409`. Mastery must not change yet.

## 27. Automatic session completion
Goal: Submitting the final answer completes the session and commits mastery in one transaction.
Description: Extend answer submission so the last answer marks the session `completed`, writes the quiz result, and applies all mastery and review updates using the mastery rules logic, all in a single database transaction. If any step fails nothing is committed. Integration-test that a forced failure leaves mastery unchanged and that a normal run updates it.

## 28. Abandon session and grade-change abandonment
Goal: An unfinished session can be abandoned explicitly or automatically when the grade changes.
Description: Add `POST /api/v1/sessions/{session_id}/abandon`, which marks an in-progress session abandoned without applying its answers to mastery or the review pool. Also make a profile grade change abandon any in-progress session while preserving all existing mastery data tied to the original words. Test that a new session can then be created.

## 29. Session results endpoint
Goal: A completed session's results can be retrieved.
Description: Add `GET /api/v1/sessions/{session_id}/results` returning score, correct and incorrect counts, missed words, words answered correctly only after a hint, and the review-word IDs with definitions and examples. Return `409` if the session is not completed. Integration-test after a full session.

## 30. Profile mastery progress endpoint
Goal: A client can retrieve a child's per-word mastery and review state.
Description: Add `GET /api/v1/profiles/{profile_id}/progress` returning each word's status, consecutive-correct count, last-practiced time, and `needs_review` flag. The review flag stays separate from the status. Scope results to the requested child and test that other children's data is excluded.

## 31. Parent dashboard: activity and vocabulary growth
Goal: The API returns practice days and word counts for the parent dashboard.
Description: Add a dashboard endpoint (path decided in this task and documented in the API) returning completed practice days in the last 7 days, completed sessions by date, total distinct words encountered, and counts of `MASTERED`, `LEARNING`, and `NEEDS_REVIEW` words, noting that the review flag overlaps the other counts. Only completed sessions count; abandoned or unfinished sessions do not. Return clear empty values for a new profile.

## 32. Parent dashboard: quiz accuracy, review words, and history
Goal: The API returns accuracy, words needing attention, and recent sessions.
Description: Extend the dashboard data with correct answers, total submitted answers, and accuracy for the last 7 and 30 days, using submitted answers from completed sessions only; the child's current review-pool words with their grade; and a newest-first session history (date, type, word count, correct/incorrect counts, status). Abandoned sessions appear in history but not in metrics. Test the windows and exclusions.

## 33. OpenAPI export script
Goal: One command writes FastAPI's schema to the committed `openapi.yaml`.
Description: Write a `uv run` script that exports the app's OpenAPI 3.1 document to `openapi.yaml` at the repository root and commit the result. Review the exported file for the `204` on the active-session route, the `oneOf` session request, structured `409` bodies, and the flattened `Profile` schema, and fix annotations where they are missing.

## 34. Generated frontend API types
Goal: The frontend has TypeScript types generated from `openapi.yaml`.
Description: Add `openapi-typescript` to `frontend/`, a script that generates types from the root `openapi.yaml`, and the generated file. Document how to regenerate after an API change. No screens change in this task; it only has to compile.

## 35. Update the frontend service interface and mock service
Goal: The mock service follows the current spec and the generated API types.
Description: Rework `frontend/src/services/types.ts` to derive from the generated types (snake_case fields, `learning`/`quiz` phases with a separate status, active-session 200/204 flow, answers by word ID, automatic completion, no repeated words, insufficient-words error, abandon, dashboard data). Keep the mock service minimal: it implements the same interface and returns simple, contract-valid data, without re-implementing the backend's selection and mastery rules. Update its existing tests.

## 36. HTTP service and mock-mode flag
Goal: The frontend can talk to the real API or the mock, selected by an environment variable.
Description: Implement an `HttpService` that satisfies the service interface using a small typed `fetch` wrapper pointed at a configurable API base URL, mapping `404`, `409`, and `422` responses into recoverable errors. Choose between it and the mock service with a single env flag. Add Vitest tests against a mocked `fetch`.

## 37. Profile management screens against the new service
Goal: Profile create, edit, select, and delete work end to end with the spec's safeguards.
Description: Update the profile picker and dialogs to the new service interface. Deletion requires typing exactly `DELETE` in uppercase and a separate final confirmation, and the UI must state that profiles are shared and not private. Show clear errors when a save fails and never claim data was saved.

## 38. Learning flow with resume
Goal: A child can learn their daily words one card at a time and resume after a refresh.
Description: On profile select, check for an active session and resume it; otherwise offer a new session, including the insufficient-content explanation. Show one word per card with definition, example, syllables, and a progress bar with a numeric count like "3 of 10", persist each advance, and offer a visible Start quiz button at the end. Include an Exit session option with confirmation. If the grade's content cannot be loaded or a progress save fails, show a clear error with a retry and never claim progress was saved.

## 39. Quiz flow with hints and feedback
Goal: A child can answer each question once and get immediate feedback.
Description: Show one meaning question per word with four large answer choices and an optional hint that reveals the example sentence. After submitting, show correct or incorrect feedback with the explanation, using more than color alone, and do not allow changing the answer or skipping ahead. Restore previously submitted feedback after a refresh.

## 40. Results screen
Goal: A child sees a friendly summary after the final answer.
Description: Show the score, correct and incorrect counts, missed words, and words answered correctly after a hint labelled as needing review, with a way to review their definitions and examples. Offer a retry that starts a targeted review session for those words. Handle loading and error states with a retry.

## 41. Parent dashboard screen
Goal: A separate read-only progress view for the selected child.
Description: Add a dashboard route reachable from the child's profile that shows practice days, vocabulary counts, 7- and 30-day accuracy with clearly labelled time windows, words needing attention, and recent session history, all from the API. Show an empty state explaining progress appears after the first completed session, and include the notice that this view is not private or protected.

## 42. Responsive layout and accessibility pass
Goal: Every screen works on desktop, tablet, and a narrow phone with no horizontal scrolling.
Description: Review the profile, learning, quiz, results, and dashboard screens at representative desktop, tablet, and narrow phone widths, and fix layout problems (stack dashboard cards, keep touch targets comfortable). Check keyboard operation, focus behavior, contrast, and that feedback never relies on color alone. Record the breakpoints chosen and the viewports checked.

## 43. Backend Dockerfile
Goal: The backend builds into a runnable container image.
Description: Write `backend/Dockerfile` that installs dependencies from `uv.lock` with `uv sync --frozen`, copies the app and data, and starts the FastAPI server. Verify the container serves `/api/v1/health`.

## 44. Frontend Dockerfile
Goal: The frontend builds into a runnable container image.
Description: Write `frontend/Dockerfile` that builds the app and serves it. The imported TanStack Start project defaults to a Cloudflare build target, so configure Nitro's Node server preset for the container and leave the rest of the app unchanged. Verify the container serves the app and can reach a configurable API URL.

## 45. Full stack with one Docker Compose command
Goal: `docker compose up` runs the frontend, backend, and PostgreSQL together.
Description: Extend `docker-compose.yml` with backend and frontend services, ordering them behind the database healthcheck. Run migrations on backend start, provide a documented way to ingest vocabulary, and resolve browser-to-API access with CORS configuration or a proxy path. Verify that created profiles persist across a restart.

## 46. Backend end-to-end lifecycle integration test
Goal: One integration test walks a whole learning session through the API.
Description: Using the integration harness and development fixtures, create a profile, start a daily session, advance through every learning card, move to the quiz, answer every word, and confirm automatic completion, results, mastery updates, and the dashboard figures. Include a refresh-style re-read of the session mid-way to confirm order is preserved.

## 47. CI: run tests on every pull request
Goal: GitHub Actions runs backend and frontend tests on each pull request.
Description: Add a workflow that sets up `uv` and bun, starts PostgreSQL as a service container, applies migrations, and runs the backend and frontend suites. A failing test must fail the check. Document the workflow's trigger and required services.

## 48. CI: OpenAPI drift check
Goal: CI fails when the committed `openapi.yaml` differs from a fresh export.
Description: Add a CI step that runs the export script and fails if the output differs from the committed file, printing the diff. Document in the contributing notes that API changes require re-exporting the file and regenerating the frontend types.

## 49. Deploy the application to a public URL
Goal: The full app is reachable on the public internet.
Description: Choose a hosting provider as the first step (the choice is deliberately open until the app runs locally), then deploy the backend with a managed PostgreSQL database and the frontend, configure environment variables and CORS, run migrations, and ingest the vocabulary. Record the public frontend and API URLs. The deployment must clearly carry the shared-demo, no-authentication warning.

## 50. Continuous deployment on merge
Goal: Merging to the main branch deploys automatically after tests pass.
Description: Wire the pipeline so a merge to `main` runs the tests and then triggers the deployment from the previous task, for example through the host's GitHub integration gated on the CI check. Document how to roll back to the previous deployment.

## 51. AGENTS.md and modular project docs
Goal: A root `AGENTS.md` that describes the project and links to the detailed docs.
Description: Write `AGENTS.md` covering what WordWise is, repository layout, how to run, test, and regenerate the API contract, key rules (no accounts, spec as source of truth, frontend repo untouched), and links to modular docs such as the spec, architecture, process, and agent team documents. Keep it concise and make every link resolve.

## 52. Agent team and process documentation
Goal: A document defining the agent roles and how they work together.
Description: Write `docs/agents.md` defining each role (for example backend, frontend, tests, reviewer), its responsibilities and boundaries, and the process: pick a task from the tracker, work on a branch, open a pull request referencing the issue, pass CI, then merge. Add `docs/process.md` if needed for branching and review conventions.

## 53. Public task tracker seeded from the backlog
Goal: A publicly accessible tracker with acceptance criteria for each task.
Description: Create GitHub Issues (or a public Project board) from this backlog and the spec's acceptance checklist, each with its goal and acceptance criteria. Make sure the repository is public, link the tracker from the README, and have pull requests reference and close issues so the tracker shows evidence of use.

## 54. README for assessors
Goal: A README that lets a reviewer understand, run, and assess the project.
Description: Write the English README covering the problem, system functionality and expected behavior, the tech stack, how to start the full stack with one command, how to run tests, API documentation location, the deployed URLs, the CI/CD summary, and links to the spec, architecture, tracker, `AGENTS.md`, and agent docs. State only what is final and true; do not mention tabled items as delivered, and do not promise offline access (the spec defers it).

## 55. Acceptance checklist verification
Goal: Every item in the spec's section 16 checklist is verified and recorded.
Description: Walk through the acceptance checklist in `_docs/plan.md` against the running application (locally and deployed), noting pass or fail and a fix task for each failure. Confirm the single-command start, the single-command tests, and that the UI never implies privacy. Record the results in a document the README links to.
