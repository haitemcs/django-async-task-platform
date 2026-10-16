# Async Task Processing Platform

A Django REST Framework project for learning reliable asynchronous job processing with Celery, Redis, and PostgreSQL.

**Project status:** infrastructure hardening in progress. The API can create and track task records and dispatch a Celery job, but the worker's `_perform_task()` function is still a placeholder. The repository does **not** yet perform a meaningful business workload.

## Architecture

Docker Compose defines these services:

- **web** — Django served by Gunicorn
- **db** — PostgreSQL 15
- **redis** — Redis 7, used as Celery's broker and the idempotency cache
- **celery_worker** — Celery worker process
- **nginx** — reverse proxy on port 80

Intended request flow:

```text
Client -> Nginx -> Django REST API -> PostgreSQL
                              |
                              +-> after commit -> Redis broker -> Celery worker
                                                                  |
                                                                  +-> PostgreSQL result/status
```

The API saves the task row inside a database transaction and schedules Celery dispatch with `transaction.on_commit()`. This prevents a worker from being dispatched before the database transaction commits. It does not provide a durable transactional outbox if Redis publishing fails after the database commit.

## Tech stack

- Python 3.13 container image
- Django and Django REST Framework
- Celery and Redis
- PostgreSQL 15
- Simple JWT
- django-filter and drf-spectacular
- pytest and pytest-django
- Docker Compose, Gunicorn, and Nginx

Pinned Python dependencies are listed in `requirements.txt`.

## Current implementation

- Authenticated task creation, listing, detail, update, and delete routes
- Registration and JWT obtain/refresh routes
- Task records with owner, status, result data, error message, retry count, and timestamps
- Owner-scoped task querysets and read-only server-managed task fields
- Dispatch after successful database commit
- Celery retry/backoff configuration and task-state updates
- Idempotency response caching scoped by request route and credential identity; a reused key with a different payload returns HTTP 409
- Redis lock to reject concurrent duplicate requests while the first request is running
- Liveness and readiness endpoints; readiness responses do not expose raw dependency exception messages
- Compose health checks for PostgreSQL, Redis, and the web service
- CI workflow that checks Django configuration, migrations, and tests against PostgreSQL and Redis

**Idempotency limitation:** this middleware is best-effort. If Redis is unavailable, the request is allowed through without idempotency protection. A process crash after performing a side effect but before caching the response can also permit the side effect to be repeated. Critical workflows should use application-level idempotency and, where necessary, a durable job/outbox design.

**Workload limitation:** `tasks/tasks.py::_perform_task()` currently returns a hardcoded placeholder result. The next product step is to implement and test a real processing workload; additional infrastructure should not be added just for its own sake.

## Project layout

```text
django-async-task-platform/
├── config/                 # Django settings, URLs, WSGI/ASGI, Celery config
├── core/                   # Health checks and middleware
│   └── tests/              # Health and idempotency middleware tests
├── tasks/                  # Task model, API, serializers, Celery task
├── docker/nginx.conf
├── scripts/entrypoint.sh
├── .github/workflows/      # CI
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
├── requirements.txt
└── LICENSE
```

A local `db.sqlite3` file may exist in the repository, but the configured Django database backend is PostgreSQL and the SQLite file is not used by the Compose setup.

## Run locally with Docker Compose

Requirements: Docker Engine and Docker Compose.

1. Create a local environment file from the example if you do not already have one:

   ```bash
   cp .env.example .env
   ```

2. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

   PostgreSQL and Redis have health checks. The web service waits for both to become healthy, and Nginx waits for the web service's liveness check.

3. Apply database migrations:

   ```bash
   docker compose exec web python manage.py migrate
   ```

4. Run Django checks and tests:

   ```bash
   docker compose exec web python manage.py check
   docker compose exec web python manage.py makemigrations --check --dry-run
   docker compose exec web pytest -q
   ```

5. Inspect service status and logs:

   ```bash
   docker compose ps
   docker compose logs --tail=100 web celery_worker db redis nginx
   ```

Available addresses with the default port mappings:

- Nginx: http://localhost/
- Django/Gunicorn directly: http://localhost:8000/
- Liveness: http://localhost/health/live/
- Readiness: http://localhost/health/ready/

The readiness endpoint checks PostgreSQL and Redis connectivity. It does not prove that a Celery worker is consuming jobs successfully.

Stop services without deleting database data:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to remove the persistent PostgreSQL volume.

The values in `.env.example` are for local development only. Set strong, private credentials and a proper `DJANGO_SECRET_KEY` before deploying anywhere outside a local development environment. Changing PostgreSQL environment variables does not rewrite credentials inside an already initialized database volume.

## Tests and CI

Run the local test suite with:

```bash
docker compose exec web pytest -q
```

GitHub Actions runs Django checks, checks for missing migrations, applies migrations, and runs the test suite using PostgreSQL and Redis service containers.

Passing unit tests does not replace an end-to-end test with a live Celery worker. Worker crash recovery, broker outages, and exactly-once side effects are not guaranteed by the current design.

## Roadmap

- [x] Create task API and persist task lifecycle fields
- [x] Dispatch Celery tasks after database commit
- [x] Add baseline idempotency response caching and middleware tests
- [x] Add health endpoint tests and dependency health checks
- [x] Add CI for PostgreSQL, Redis, Django checks, and tests
- [ ] Verify CI passes on GitHub and run the stack locally
- [ ] Add live-worker integration tests and concurrent idempotency tests
- [ ] Design durable dispatch/recovery behavior for the database-to-broker gap
- [ ] Implement a real workload, such as CSV validation and summary report generation
- [ ] Add performance measurements and document system limits

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
