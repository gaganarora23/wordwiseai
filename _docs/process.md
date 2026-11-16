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

1. Pick the next open issue labelled `mvp`: the lowest number whose dependencies are done
2. PM grooms it
3. Engineer creates a feature branch `task-<N>-<slug>` from main, implements the issue there and pushes the branch
4. QA verifies it on that branch
5. On FAIL, back to step 3 on the same branch with the QA comment as input. After 3 failed QA rounds, stop and ask the user
6. On PASS, the orchestrator closes the issue and opens a pull request from the feature branch to main that references the issue
7. A person merges the pull request. The orchestrator does not merge
8. Repeat until the backlog is empty

Branches and dependencies

- One feature branch and one pull request per issue
- Branch from an up-to-date main. If an issue depends on one whose pull request is not merged yet, wait for the merge before starting it. If the user says not to wait, branch from the earlier issue's feature branch instead and say so in the pull request
- Independent issues can start from main while other pull requests are open

Rules

- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator closes the issue only after QA outputs PASS
- Nobody merges to main except a person