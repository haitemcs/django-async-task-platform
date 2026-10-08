# Async Task Processing Platform

A Django REST API for submitting and processing background tasks asynchronously with Celery, Redis, and PostgreSQL.

The project is designed to demonstrate practical backend concepts including asynchronous job processing, task state tracking, database persistence, retry handling, request idempotency, health checks, and containerized development.

---

## Architecture

The application follows a producer-consumer architecture:

```text
                         ┌─────────────────────┐
                         │       Client        │
                         │ Web / Postman / CLI │
                         └──────────┬──────────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │    Nginx    │
                             │ Reverse     │
                             │ Proxy       │
                             └──────┬──────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │   Django    │
                             │     DRF     │
                             └──┬───────┬──┘
                                │       │
                       persist  │       │ enqueue
                                │       │
                                ▼       ▼
                         ┌──────────┐ ┌─────────┐
                         │PostgreSQL│ │  Redis  │
                         └──────────┘ └────┬────┘
                                           │
                                           ▼
                                    ┌────────────┐
                                    │   Celery   │
                                    │   Worker   │
                                    └─────┬──────┘
                                          │
                                          ▼
                                     PostgreSQL
```

### Task Lifecycle

Tasks are tracked through explicit states:

```text
PENDING
   │
   ▼
PROCESSING
   │
   ├──────────────► COMPLETED
   │
   └──────────────► FAILED
```

The intended flow is:

1. The client submits a task through the API.
2. Django validates and stores the task in PostgreSQL.
3. The task is dispatched to Celery through Redis after the database transaction commits.
4. A Celery worker processes the task.
5. The task is marked as `COMPLETED` or `FAILED`.
6. Retry attempts and error information are persisted with the task.

---

## Features

- Django REST API
- PostgreSQL persistence
- Celery background workers
- Redis message broker
- Explicit task status tracking
- Retry handling with Celery
- Database transaction safety with `transaction.on_commit()`
- Request-level idempotency using `Idempotency-Key`
- User-specific task access
- Liveness and readiness health endpoints
- Docker Compose development environment
- Nginx reverse proxy
- Pytest test suite
- Environment-based configuration

---

## Tech Stack

| Component | Version / Technology |
|---|---|
| Python | 3.11 (Docker image) |
| Django | 6.1.2 |
| Django REST Framework | 3.18.3 |
| Celery | 5.6.3 |
| Redis | 7 (Docker image) |
| PostgreSQL | 15 (Docker image) |
| Database Driver | psycopg2-binary 2.9.13 |
| Testing | pytest 9.1.1 / pytest-django |
| Configuration | python-dotenv |
| Web Server | Gunicorn |
| Reverse Proxy | Nginx |
| Containers | Docker / Docker Compose |

> The versions above reflect the current repository configuration. Update this section whenever dependency or container versions change.

---

## Project Structure

```text
django-async-task-platform/
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py          # Celery application configuration
│   ├── settings.py        # Django configuration
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py
│
├── core/
│   ├── apps.py
│   ├── health.py          # Health-check endpoints
│   ├── middleware.py      # Request middleware
│   ├── urls.py
│   └── tests/
│
├── tasks/
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py          # Task domain model
│   ├── tasks.py           # Celery task definitions
│   ├── views.py
│   └── tests/
│
├── docker/
│   └── nginx.conf         # Nginx reverse-proxy configuration
│
├── scripts/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
└── requirements.txt
```

---

## Environment Configuration

Create a local environment file from the example:

```bash
cp .env.example .env
```

The Docker Compose setup uses PostgreSQL and Redis service names as hosts.

Example configuration:

```ini
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web

POSTGRES_DB=async_tasks
POSTGRES_USER=async_tasks
POSTGRES_PASSWORD=async_tasks_pass
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

Never commit real secrets or production credentials.

---

## Local Development with Docker

### 1. Build and start the services

```bash
docker compose up --build -d
```

The Compose stack contains:

- PostgreSQL
- Redis
- Django/Gunicorn
- Celery worker
- Nginx

### 2. Apply migrations

```bash
docker compose exec web python manage.py migrate
```

### 3. Create a superuser

```bash
docker compose exec web python manage.py createsuperuser
```

### 4. Check the application

The current Compose configuration exposes:

- API: http://localhost:8000/
- Nginx: http://localhost/
- Health endpoints: see the API health routes in `core/urls.py`

---

## API Usage

### Authentication

If authentication is enabled in your current configuration, obtain credentials using the authentication endpoints exposed by the project.

The exact routes are defined in the project's URL configuration.

### Creating a Task

Example request:

```bash
curl -X POST http://localhost/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Idempotency-Key: task-request-001" \
  -d '{
    "title": "Process Dataset",
    "description": "Background processing job"
  }'
```

The `Idempotency-Key` is intended to prevent duplicate processing when a client retries the same request.

### Filtering Tasks

Example:

```bash
curl "http://localhost/api/tasks/?status=COMPLETED" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Use the project's URL and view configuration as the source of truth for supported query parameters.

---

## Health Checks

The project provides application health checks for container and service monitoring.

Typical endpoints include:

```text
GET /api/health/live/
GET /api/health/ready/
```

The readiness check is intended to verify that required dependencies such as PostgreSQL and Redis are available.

Example:

```bash
curl http://localhost/api/health/live/
curl http://localhost/api/health/ready/
```

---

## Testing

Run the test suite inside the web container:

```bash
docker compose exec web pytest
```

For a local Python environment:

```bash
pytest
```

---

## Celery Worker

The worker is started by Docker Compose:

```bash
docker compose up celery_worker
```

Or run it manually:

```bash
celery -A config worker --loglevel=info
```

Celery uses Redis as the message broker and result backend.

---

## Development Notes

This repository is currently focused on the backend architecture and asynchronous processing workflow.

The main engineering concepts demonstrated are:

- REST API design
- relational persistence
- asynchronous job queues
- producer-consumer architecture
- transaction boundaries
- idempotency
- task state machines
- retry handling
- service health checks
- Dockerized development
- reverse-proxy configuration
- automated testing

---

## Roadmap

Planned improvements for a production-oriented version:

- [ ] Add/complete JWT authentication
- [ ] Add OpenAPI/Swagger documentation
- [ ] Add API filtering, searching, and pagination
- [ ] Add stronger task concurrency guarantees
- [ ] Add Celery retry/backoff tests
- [ ] Add Docker healthchecks
- [ ] Add a non-root production image
- [ ] Add a dedicated production Compose configuration
- [ ] Add GitHub Actions CI
- [ ] Add structured application logging
- [ ] Add monitoring/metrics
- [ ] Add integration tests for Redis and Celery

---

## License

This project is currently intended as a portfolio and learning project.
