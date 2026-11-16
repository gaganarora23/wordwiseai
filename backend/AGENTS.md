Documents

- `_docs/process.md` - how work is organized
- Before writing tests, read `_docs/testing-guidelines.md`
- API contract and conventions: `_docs/api.md`; architecture: `_docs/architecture.md`; spec: `_docs/plan.md` section 14
- Roles and branch/PR/CI conventions: `docs/agents.md`, `docs/process.md`

Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_health.py` - one test file

Rules

- Dependencies are added in `pyproject.toml`. Do not add one without asking