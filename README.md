# Async Task Processing Platform

A Django backend project exploring asynchronous job processing with Celery and Redis, PostgreSQL persistence, task-state modeling, JWT authentication, idempotency middleware, health checks, and a Docker Compose environment.

**Project status:** in progress. The repository contains task API views and routes, but the complete runtime workflow still needs to be verified with Docker and integration tests.

## Architecture

The Compose environment defines:

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

## Tech stack

- Python 3.11 container image
- Django 6.1.2
- Django REST Framework 3.18.3
- Celery 5.6.3
- PostgreSQL 15
- Redis 7
- Simple JWT
- django-filter
- drf-spectacular
- pytest and pytest-django
- Docker Compose, Gunicorn, and Nginx

Dependencies are pinned in `requirements.txt`; service image versions are specified in `docker-compose.yml`.

## Current implementation

- A `Task` model with `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED` status choices
- Task fields for owner, title, description, result data, error message, retry count, and timestamps
- Database indexes for task status, owner plus creation date, and owner plus status
- Task API routes and owner-scoped task views
- Celery task processing code
- Idempotency middleware
- Liveness and readiness health-check endpoints
- JWT authentication, pagination, filtering, search, ordering, throttling, and OpenAPI schema settings

These features have not yet been confirmed by a successful end-to-end run. The automated tests also need to be expanded beyond placeholder coverage.

## Project layout

```text
django-async-task-platform/
├── config/                 # Django settings, URLs, WSGI/ASGI, Celery config
├── core/                   # Health checks and middleware
├── tasks/                  # Task API, model, and Celery task
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

## Run with Docker Compose

Requirements: Docker Engine and Docker Compose.

1. Optionally copy `.env.example` to `.env` and adjust the development settings.
2. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

3. Apply database migrations:

   ```bash
   docker compose exec web python manage.py migrate
   ```

4. Check Django configuration and database migration state:

   ```bash
   docker compose exec web python manage.py check
   docker compose exec web python manage.py makemigrations --check --dry-run
   ```

The Compose defaults are intended for local development only. Change credentials and the Django secret key before using this configuration outside a local environment. PostgreSQL initialization variables only create the configured role/database when the data directory is first initialized; changing these values does not rewrite an existing database volume.

Available addresses:

- Nginx: http://localhost/
- Django/Gunicorn directly: http://localhost:8000/
- Liveness check: http://localhost/health/live/
- Readiness check: http://localhost/health/ready/

The readiness endpoint checks the database and Redis dependencies. Health routes are mounted under `/health/` in `config/urls.py`.

Stop services with:

```bash
docker compose down
```

This stops containers but preserves the named PostgreSQL data volume. To avoid accidental data loss, do not remove the volume as a troubleshooting shortcut.

## Tests

Run the current test suite in the web container:

```bash
docker compose exec web pytest
```

Passing the current test suite should not be treated as proof of full task-processing correctness; meaningful API, database, idempotency, and Celery integration tests remain necessary.

## Development roadmap

- [ ] Add meaningful API, authentication, and task lifecycle tests
- [ ] Verify task submission and Celery processing end to end
- [ ] Complete idempotency behavior and tests
- [ ] Add CI and strengthen production container hardening
- [ ] Replace development-only credentials and secret-key defaults for deployment

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
