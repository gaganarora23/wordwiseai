.PHONY: test

test:
	cd backend && uv run pytest
	cd frontend && bun run test
