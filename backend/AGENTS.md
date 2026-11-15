## Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite (`make test` from the repo root runs the same)
- `uv run pytest tests/test_smoke.py` - one test file

## Rules

- Add dependencies with `uv add` (never edit `pyproject.toml` by hand or use `pip`) and commit `uv.lock`. Do not add one without asking.
