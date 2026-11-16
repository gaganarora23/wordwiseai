.PHONY: test deps test-db

# `make test` is the single entry point: it installs dependencies from the
# lockfiles, makes sure PostgreSQL is reachable, then runs both suites. Both
# suites always run, and the exit status is non-zero if either one fails.
# GNU make 3.81 and POSIX sh only.
test: deps test-db
	@rc=0; \
	(cd backend && uv run pytest) || rc=1; \
	(cd frontend && bun run test) || rc=1; \
	exit $$rc

deps:
	cd backend && uv sync --frozen
	cd frontend && bun install --frozen-lockfile

# Starts the Compose `db` service only when no database is reachable yet. It never
# stops, removes or resets anything (no `down`, no `-v`). Skipped in CI (CI=true, where a
# service container is already running) and whenever the configured host and port answer.
# A DATABASE_URL from the environment or .env is never overridden. With neither, the
# Compose defaults are used with DB_PORT (environment, then .env, default 5432); that
# URL is exported to the test run only, and no file is written.
# The shell function below is one recipe; $$ is make's escape for a literal $.
test-db:
	@envval() { [ -f .env ] && sed -n "s/^$$1=//p" .env | tail -n 1 | sed "s/^[\"']//;s/[\"']\$$//"; true; }; \
	url="$${DATABASE_URL:-$$(envval DATABASE_URL)}"; \
	dbport="$${DB_PORT:-$$(envval DB_PORT)}"; dbport="$${dbport:-5432}"; \
	if [ -n "$$url" ]; then \
		rest="$${url##*@}"; hostport="$${rest%%[/?]*}"; host="$${hostport%%:*}"; \
		case "$$hostport" in *:*) port="$${hostport##*:}";; *) port=5432;; esac; \
	else \
		user="$${POSTGRES_USER:-$$(envval POSTGRES_USER)}"; user="$${user:-wordwise}"; \
		pass="$${POSTGRES_PASSWORD:-$$(envval POSTGRES_PASSWORD)}"; pass="$${pass:-change-me}"; \
		name="$${POSTGRES_DB:-$$(envval POSTGRES_DB)}"; name="$${name:-wordwise}"; \
		host=localhost; port="$$dbport"; \
		export DATABASE_URL="postgresql+psycopg://$$user:$$pass@localhost:$$port/$$name"; \
	fi; \
	reachable() { (cd backend && uv run --frozen --no-sync python -c "import socket,sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 2).close()" "$$host" "$$port") >/dev/null 2>&1; }; \
	if [ "$$CI" = "true" ] || reachable; then exit 0; fi; \
	case "$$host" in localhost|127.0.0.1|::1|"[::1]") ;; *) exit 0;; esac; \
	command -v docker >/dev/null 2>&1 || { echo "make test: Docker is not installed and no database answers on $$host:$$port. Install Docker Desktop, or point DATABASE_URL at a running PostgreSQL."; exit 1; }; \
	docker info >/dev/null 2>&1 || { echo "make test: Docker is not running. Start Docker Desktop (or the docker daemon) and run make test again."; exit 1; }; \
	echo "Starting PostgreSQL: docker compose up -d --wait db"; \
	docker compose up -d --wait db || { echo "make test: the database did not become healthy. If port $$dbport is taken, set DB_PORT in .env or the environment (see README, Troubleshooting); run docker compose logs db for details."; exit 1; }; \
	reachable || { echo "make test: the database container is healthy but $$host:$$port does not answer. The port in DATABASE_URL must match DB_PORT (currently $$dbport); see README, Troubleshooting."; exit 1; }
