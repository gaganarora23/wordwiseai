# Working conventions: branches, pull requests, CI

The issue lifecycle (PM grooms, engineer implements, QA verifies, close) is defined once, in [`_docs/process.md`](../_docs/process.md); roles and who owns an issue at each stage are in [`docs/agents.md`](agents.md). This file only adds how the code gets from a branch to `main`.

## Flow

1. Pick the next open issue (orchestrator).
2. PM grooms it (`## PM:` comment).
3. Engineer works on a branch, never directly on `main`.
4. Engineer opens a pull request against `main` whose description references the issue (`#N`, or `Closes #N` only when the orchestrator will merge after QA PASS).
5. QA verifies the PR's code against the acceptance criteria.
6. CI must pass: the `CI / test` check from `.github/workflows/ci.yml` (backend and frontend suites against PostgreSQL), which runs on every pull request and on pushes to `main`.
7. Merge the pull request (orchestrator, after QA PASS and green CI), then close the issue.

## Branch naming

Branches are named after the work, in lowercase with hyphens. Existing examples: `task-1-empty-project`, `task-2-import-frontend`, `mvp-tasks-3-14`, `mvp-tasks-15-20`, `qa-fixes-and-deploy-prep`. Use `task-<n>-<short-name>` for one issue, or `<scope>-tasks-<first>-<last>` or a descriptive name when one branch carries several related issues. A branch carrying several issues must name each in its commit messages and PR description.

## Commits and pull requests

- Commit regularly; commit messages name the issue number (for example `(#17, #18)`).
- PR title says what changed; the description lists the issues it covers.
- Review convention: QA is the independent reviewer. It reads the issue and the running code, not the engineer's summary. The author of a change does not approve it.
- Known gap: earlier issues were closed on QA PASS while still on an unmerged branch. Merge first when possible, so closed means in `main`.

Deployment on merge to `main`, its setup and rollback steps: [`docs/deployment.md`](deployment.md).
