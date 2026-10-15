# Async Task Processing Platform

A Django backend project exploring asynchronous job processing with Celery and Redis, PostgreSQL persistence, task-state modeling, JWT configuration, idempotency middleware, health checks, and a Docker Compose environment.

**Project status:** in progress. The repository includes task REST API views, JWT routes, Celery task processing, health checks, and Docker Compose configuration. Run the setup and checks below to verify the full workflow in your environment.

## Architecture

The current Compose configuration defines these services:

- **web** — Django served by Gunicorn
- **db** — PostgreSQL 15
- **redis** — Redis 7
- **celery_worker** — Celery worker
- **nginx** — reverse proxy on port 80

Intended task flow:

```text
Client -> Django API -> PostgreSQL
                    -> Redis -> Celery worker
```

The intended submission flow saves a task in PostgreSQL and dispatches processing to Celery after the database transaction commits.

## Tech stack

- Python 3.11 container image
- Django 6.1.2
- Django REST Framework 3.18.3
- Celery 5.6.3
- PostgreSQL 15
- Redis
- Simple JWT
- django-filter
- drf-spectacular
- pytest and pytest-django
- Docker Compose, Gunicorn, and Nginx

Dependency versions are pinned in `requirements.txt`; the database and Redis image tags are specified in `docker-compose.yml`.

## Current implementation

- A task model with `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED` status choices
- Task fields for owner, title, description, result data, error message, retry count, and timestamps
- Database indexes for task status, owner plus creation date, and owner plus status
- A Celery task for processing submitted tasks
- Idempotency middleware
- Liveness and readiness health-check routes
- JWT authentication, pagination, filtering, search, ordering, throttling, and OpenAPI schema settings configured in Django

Task API routes are defined in `tasks/urls.py`; verify them with the API checks and tests before treating the entire workflow as production-ready.

## Project layout

```text
django-async-task-platform/
├── config/                 # Django settings, URLs, WSGI/ASGI, Celery config
├── core/                   # Health checks and middleware
├── tasks/                  # Task model and Celery task
├── docker/nginx.conf
├── scripts/entrypoint.sh
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
├── requirements.txt
├── LICENSE
└── README.md
```

A local `db.sqlite3` file is also currently tracked, but the configured Django database backend is PostgreSQL. It is not needed for the intended Compose setup.

## Run with Docker Compose

Requirements: Docker Engine and Docker Compose.

From the repository root:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
```

Available addresses from the current Compose port mappings:

- Nginx: http://localhost/
- Django/Gunicorn directly: http://localhost:8000/
- Liveness check: http://localhost/health/live/
- Readiness check: http://localhost/health/ready/

The health routes are currently registered without an `/api/` prefix. The readiness endpoint checks dependencies as implemented in `core/health.py`.

Compose and Django read the same `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` environment variables. The fallback values are for local development only; set strong secrets outside the repository before any real deployment. If you already have a persistent PostgreSQL volume initialized with different credentials, changing environment variables does not rewrite the existing database role/password.

Stop services with:

```bash
docker compose down
```

## Tests

Run the current test suite in the web container:

```bash
docker compose exec web pytest
```

The test suite is still limited and should not be taken as evidence that the complete asynchronous task API is implemented.

## Development roadmap

- [x] Implement authenticated task creation, listing, and detail endpoints
- [x] Connect API submissions to Celery after the database transaction commits
- [ ] Persist processing results and failure details
- [ ] Complete idempotency behavior and tests
- [ ] Add task lifecycle, retry, and integration tests
- [x] Read database credentials from environment variables
- [ ] Add CI and strengthen production container hardening

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
