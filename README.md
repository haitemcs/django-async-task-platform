# Async Task Processing Platform

A Django backend project exploring asynchronous job processing with Celery and Redis, PostgreSQL persistence, task-state modeling, JWT configuration, idempotency middleware, health checks, and a Docker Compose environment.

**Project status:** in progress. The repository contains the task model and a sample Celery task, but the task REST API views and end-to-end submission workflow are not implemented yet. This README distinguishes existing code from planned behavior.

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

The complete task-submission and processing flow is still under development.

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
- A sample Celery function named `process_background_job`
- Idempotency middleware
- Liveness and readiness health-check routes
- JWT authentication, pagination, filtering, search, ordering, throttling, and OpenAPI schema settings configured in Django

Some configured capabilities are not yet connected to a complete task API. In particular, `tasks/views.py` currently contains only the Django placeholder, so task create/list/detail endpoints should not be assumed to work.

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

The Compose file currently supplies database credentials directly in the service configuration, and Django settings currently use a hard-coded database password. Treat this as development-only configuration; replace these values with environment-driven secrets before any real deployment. Do not use the development defaults in production.

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

- [ ] Implement authenticated task creation, listing, and detail endpoints
- [ ] Connect API submissions to Celery after the database transaction commits
- [ ] Persist processing results and failure details
- [ ] Complete idempotency behavior and tests
- [ ] Add task lifecycle, retry, and integration tests
- [ ] Move all credentials to environment variables
- [ ] Add CI and strengthen production container hardening

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
