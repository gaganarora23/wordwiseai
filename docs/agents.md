# Agent team

WordWise is built by an AI agent team. Roles are instructions given to subagents; the full lifecycle is in [`_docs/process.md`](../_docs/process.md) and the branch, PR and CI conventions are in [`docs/process.md`](process.md). Per-role instructions live in `_docs/team/`.

## Roles that exist

| Role | Instructions | Owns |
|---|---|---|
| Orchestrator (main session) | `_docs/process.md` | Picking the next issue, launching the other roles, relaying hand-offs, closing the issue after QA PASS, merging |
| PM | [`_docs/team/pm.md`](../_docs/team/pm.md) | Grooming: the issue's template sections, checkable acceptance criteria, labels, follow-up issues |
| Engineer | [`_docs/team/software-engineer.md`](../_docs/team/software-engineer.md) | Implementation and its tests, backend and frontend alike, the branch, commits and PR |
| QA | [`_docs/team/qa-engineer.md`](../_docs/team/qa-engineer.md) | Verification against the acceptance criteria, the PASS or FAIL verdict; the project's test and review role |

There is no separate backend, frontend, tests or reviewer agent. One engineer role covers backend (`backend/`) and frontend (`frontend/`); the area is named by the issue and by `backend/AGENTS.md` and `frontend/AGENTS.md`. QA is the tests-and-review role: it runs the suites and judges the result independently. Each role's work is still checked by the next one.

## Inputs, outputs and limits

| Role | Input | Output (hand-over artifact) | Must NOT |
|---|---|---|---|
| Orchestrator | The backlog (GitHub issues) | Launches subagents; the closing comment "Closing: QA PASS" | Groom, implement or test itself; close an issue before QA PASS |
| PM | The issue as filed, `_docs/task-template.md` | The rewritten issue body plus a comment starting `## PM:`; `mvp` or `post-mvp` label; follow-up issues for anything moved out of scope | Write code; silently drop scope; leave an out-of-scope item without a linked issue |
| Engineer | The groomed issue; on a retry, the `## QA: FAIL` comment | Commits on the issue's branch, a PR, and a comment starting `## Engineer: implemented` (or `## Engineer: fixed QA failure`) | Change the acceptance criteria (raise a comment instead); close the issue; add a dependency without asking; edit the original Lovable repo (`grade-five-word-garden`) |
| QA | The issue's acceptance criteria and the running code | A comment starting `## QA: PASS` or `## QA: FAIL` with a verdict per criterion, the test command and its result | Fix code; trust the engineer's own description; give PASS if any one criterion fails |

## Which role owns an issue

An issue has exactly one owner at a time, decided by its stage. Issues carry no role label; the latest comment heading shows the stage.

| Stage | Owner | Stage ends when |
|---|---|---|
| Open, ungroomed | PM | `## PM:` comment posted and the issue body follows the template |
| Groomed | Engineer | `## Engineer: implemented` comment posted, PR open |
| Implemented | QA | `## QA: PASS` or `## QA: FAIL` posted |
| QA FAIL | Engineer | `## Engineer: fixed QA failure` posted, then QA again |
| QA PASS | Orchestrator | PR merged after `CI / test` passes, issue closed |

## Project rules every role follows

- Accounts are out of scope: no registration, login or authentication (`_docs/plan.md`).
- `_docs/plan.md` is the source of truth for behavior; if code and spec disagree, raise it in an issue comment.
- The original Lovable repository (`grade-five-word-garden`) is never modified; the frontend in `frontend/` is a copy.
