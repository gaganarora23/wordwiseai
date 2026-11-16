# Deployment (continuous deployment to Render)

Every merge to `main` runs the tests and, only if they pass, asks Render to deploy the backend (API) and the frontend (web). The pipeline is the `deploy` job in `.github/workflows/ci.yml`. The Render services themselves are defined in `render.yaml` (#49).

## Flow

```
pull request --> CI / test        (deploy job is skipped on pull requests)
      |
   merge to main
      |
      v
   test  --pass-->  deploy  -->  Render builds and releases API and web
      |
    fail --> deploy is skipped, nothing is deployed
```

- `test` is the same job that runs on pull requests (backend and frontend suites against PostgreSQL).
- `deploy` declares `needs: test` and only runs on `push` to `main`. It has `permissions: contents: read` and a `concurrency` group (`deploy-production`, no cancellation), so two quick merges deploy one after the other and the later one is not lost.
- The job calls two Render deploy hooks with `curl --fail`, so a non-2xx answer turns the job red. The hook URLs come from secrets through `env:`, so GitHub masks them and they are never echoed. The log prints the Render deploy id (`dep-...`) when the hook returns one.
- Render auto-deploy is off, so a deploy only starts from the hook or manually from the dashboard.
- If a secret is not set, its step prints a notice and is skipped without failing, so merging before Render is configured does not turn `main` red. Once Render is set up, a missing secret means that service is silently not deployed, so check the notices in the run log.
- Re-running a failed deploy job is safe: hooks can be repeated and ingestion is idempotent.
- The free tier can take several minutes to build, and the first request after a deploy can be slow (cold start).

## One-time setup (user)

1. Create the services from `render.yaml` (Blueprint, #49).
2. For each service open Settings > Deploy Hook in Render and copy the URL. The URL is a credential: do not paste it into the repository, issues or logs.
3. In GitHub: Settings > Secrets and variables > Actions > New repository secret. Create exactly:
   - `RENDER_DEPLOY_HOOK_API`: the backend service's hook URL
   - `RENDER_DEPLOY_HOOK_WEB`: the frontend service's hook URL
4. Check in the Render dashboard that Auto-Deploy is Off for both services.

Fork pull requests do not receive these secrets and never run `deploy`.

## A failing test prevents a deploy

`deploy` needs `test`. If `test` fails, GitHub shows `test` red and `deploy` as skipped in the run graph, no hook is called and Render shows no new deploy for that commit. Because pull requests never run `deploy`, a failing test is visible on a draft PR as `test` red with no `deploy` job at all.

## What happens on each deploy

The backend container starts with `backend/docker-entrypoint.sh`:

1. `alembic upgrade head` applies pending database migrations (a no-op when up to date).
2. `python -m app.services.vocabulary_ingestion` loads the vocabulary idempotently: existing words are left unchanged (the log shows `unchanged: 500`), nothing is duplicated or deleted, and profiles created earlier remain.
3. `uvicorn` serves the API.

The frontend only needs the already-known backend URL, so the two hooks can finish in either order.

## If the free database expired (after 30 days)

A free Render PostgreSQL database is deleted 30 days after creation. `render.yaml` defines it as `wordwise-db`, and the API's `DATABASE_URL` is taken from it, so recreating it is quick. Every profile created in the demo is lost; only the schema and the 500 vocabulary words come back.

1. In Render, sync the Blueprint manually (the Blueprint's manual sync action) so the missing `wordwise-db` is created again. If you prefer, create a new free PostgreSQL database named `wordwise-db` in the same region instead; then, if `wordwise-api` no longer points at it, set its `DATABASE_URL` environment variable to the new database's internal connection string.
2. Redeploy `wordwise-api`: use Manual Deploy on the service, or merge to `main` so the CI `deploy` job calls the hook. On start `backend/docker-entrypoint.sh` runs `alembic upgrade head` and the idempotent vocabulary ingestion, so the schema and words are rebuilt automatically. In the API logs look for `Running upgrade` and `Created: 500`.
3. Check `https://wordwise-api-xji2.onrender.com/api/v1/health` (expect `{"status":"ok"}`) and `/api/v1/grades/5/words` (expect 50 words), then open the app and create profiles again.
4. To keep the data instead, upgrade the database to a paid plan before it expires.

## Rollback

### Path A: Render dashboard

1. Open the service in Render, then Events (or Deploys).
2. Pick the previous successful deploy and choose Rollback. Do this for each service that needs it (API and web).
3. The next merge to `main` deploys new code again through the hook; no re-enable step is needed.

A dashboard rollback does not undo database migrations. If the bad deploy included a migration, the old code now runs against the newer schema. Decide whether the migration is backward compatible; if not, downgrade manually (`alembic downgrade -1` against the production database, from a trusted shell) or ship a fix-forward migration.

### Path B: git revert through a pull request

1. `git revert <merge commit>` on a branch and open a pull request.
2. CI runs `test` on the PR; after merge, `test` and the same `deploy` job run, so the reverted code is deployed through the normal pipeline.
3. Migrations are not undone by a revert either; see the note above.

## Rollback performed

NOT yet performed. The live deployment does not exist yet. To be filled in once it does:

- Date:
- Service(s) and Render deploy ids (bad deploy, rolled-back-to deploy, roll-forward deploy):
- Evidence (screenshots or links) that the previous version was live at the public URL, and that the app was moved forward again:
