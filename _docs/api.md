# API

The backend is FastAPI. Base path `/api/v1`; JSON bodies.

## Where the contract lives

- Live, generated from the code: `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/openapi.json` (OpenAPI 3.1). Start the backend first (`docker compose up --build`, or see `README.md`).
- Endpoint table with success and error codes: the "API" section of `README.md`.
- Intended full contract (all endpoints, including sessions, quiz and dashboard that are not built yet): section 14 of `_docs/plan.md`.

Not built yet: the planned standalone `openapi.yaml` at the repository root, the script that exports the schema, the CI drift check and the generated frontend types (`openapi-typescript`). They are described in `_docs/architecture.md` and tracked as later tasks in `_docs/tasks.md`. Until then `/openapi.json` is the machine-readable contract and no regenerate command exists.

## Conventions (from `_docs/plan.md` section 14.2)

- UUID identifiers and ISO 8601 timestamps.
- `404` for a missing resource, `409` for invalid session state or conflicts, `422` for request validation failures.
- Unknown or extra request fields are rejected with `422`.
- No authentication: the product has no accounts (see `_docs/plan.md`, non-goals).
- Change an endpoint in the code and keep `_docs/plan.md` section 14 and the `README.md` API table in step.
