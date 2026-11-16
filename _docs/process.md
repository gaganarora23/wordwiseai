- Tasks are GitHub issues, one at a time
- Read the acceptance criteria before starting and before closing
- Commit regularly

Labels 
- `mvp` needed for V0 or MVP defined in `_docs/plan.md`
- `post-mvp` work not needed now for V0 but can be done in the future.

Roles
- PM - grooms a task before anyone implements it, follows _docs/team/pm.md
- Engineer - implements one groomed task, follows _docs/team/software-engineer.md
- QA - checks the result against the acceptance criteria, follows _docs/team/qa-engineer.md


Orchestrator

The main session is the orchestrator. It launches the PM, the engineer
and QA as subagents. It does not groom, implement or test itself.

Lifecycle

1. Pick the next open issue from the backlog
2. PM grooms it
3. Engineer implements it
4. QA verifies it
5. On FAIL, back to step 3 with the QA comment as input
6. On PASS, close the issue
7. Repeat until the backlog is empty

Rules

- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator closes the issue only after QA outputs PASS

Branches, pull requests, CI and merge conventions are in `docs/process.md`.
Role definitions, limits and who owns an issue at each stage are in `docs/agents.md`.
Each role hands over by an issue comment starting `## PM:`, `## Engineer:` or `## QA:`.
