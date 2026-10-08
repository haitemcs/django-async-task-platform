# Async Task Processing Platform

A production-oriented, asynchronous task processing engine built with Django 5.2, Django REST Framework, Celery, Redis, and PostgreSQL. Demonstrates explicit state machines, non-blocking asynchronous dispatch, exponential backoff retries, request-level idempotency, user resource isolation, health probes, zero-root container security, and CI automation.

---

## Architecture Overview

The system follows an asynchronous, decoupled producer-consumer pattern. API requests accept payload validation upfront, persist the task in an explicit `PENDING` status inside PostgreSQL, and schedule the background work via a post-commit transaction hook to Celery through Redis.

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
                             │  Gunicorn   │
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

### Critical Task Lifecycle

Tasks strictly move through a deterministic finite-state machine to guarantee traceability across retries and failures:

```text
                         ┌───────────────┐
                         │    PENDING    │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  PROCESSING   │
                         └───────┬───────┘
                                 │
                         ┌───────┴────────┐
                         ▼                ▼
                  ┌────────────┐   ┌────────────┐
                  │ COMPLETED  │   │   FAILED   │
                  └────────────┘   └────────────┘

```

1. **`POST /api/tasks/`**: Request authenticated and validated.
2. **Database Persistence**: Task record created with state `PENDING`.
3. **Transaction Safety**: `transaction.on_commit()` pushes `task.id` to Redis only after the database transaction succeeds, preventing race conditions (e.g., workers attempting to process a task before it is visible in PostgreSQL).
4. **Asynchronous Execution**: Celery transitions the state to `PROCESSING`, executes business logic, and records `COMPLETED` or `FAILED` states along with error messages and attempt counts.

---

## Core Features

* **State Machine Workflow**: Explicit transitions (`PENDING` $\rightarrow$ `PROCESSING` $\rightarrow$ `COMPLETED` / `FAILED`) with persistent execution tracking.
* **Resilient Execution & Exponential Backoff**: Celery tasks automatically retry transient errors up to 3 times with exponential backoff (`retry_backoff=True`) up to a maximum delay.
* **Idempotent Task Ingestion**: Custom `Idempotency-Key` HTTP header middleware backed by Redis prevents duplicate task execution caused by network retries or client timeouts.
* **Multi-Tenant Data Isolation**: Multi-tenant queryset filtering enforces hard boundaries—attempting to retrieve another user's task returns an explicit `404 Not Found` rather than a `403 Forbidden` to prevent object enumeration.
* **Observability & Health Probes**: Split liveness (`/health/live/`) and readiness (`/health/ready/`) endpoints for Kubernetes or container orchestration. Structured stdout logging for log aggregation.
* **Production-Ready Security & Serving**: Dedicated multi-stage unprivileged (`USER django`) container build served via Gunicorn behind an Nginx reverse proxy with static asset caching.
* **Comprehensive API Suite**: JWT Authentication, OpenAPI 3.0 schema generation via `drf-spectacular`, filtering, searching, and pagination out of the box.

---

## Tech Stack

* **Core Framework**: Python 3.12, Django 5.2, Django REST Framework 3.16
* **Authentication & Security**: SimpleJWT, Custom Idempotency Middleware
* **Async Processing**: Celery 5.5, Redis 7
* **Database**: PostgreSQL 16 (`psycopg` v3 driver)
* **Web & WSGI Server**: Nginx, Gunicorn
* **API Documentation**: OpenAPI 3, Swagger UI (`drf-spectacular`)
* **Testing & Quality**: `pytest`, `pytest-django`, `ruff`
* **Containerization**: Docker, Docker Compose

---

## Project Structure

```text
async-task-platform/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated test & lint workflow
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py                # Celery app initialization & auto-discovery
│   ├── settings.py              # Environment-driven configuration
│   ├── urls.py                  # Global routing & OpenAPI endpoints
│   └── wsgi.py
├── tasks/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── middleware.py            # Redis-backed idempotency protection
│   ├── models.py                # Task domain model & indexing
│   ├── pagination.py            # Standardized page-number pagination
│   ├── serializers.py          # DRF validation & register serializers
│   ├── tasks.py                 # Resilient Celery task logic with retries
│   ├── urls.py                  # Task API routes & health probes
│   ├── views.py                 # Task ViewSet & probe logic
│   └── tests.py                 # pytest suite covering isolation & auth
├── nginx/
│   └── nginx.conf               # Reverse proxy & static routing
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile                   # Development container spec
├── Dockerfile.prod              # Multi-stage non-root production spec
├── Makefile                     # Helper developer commands
├── docker-compose.yml           # Local dev setup with hot-reload
├── docker-compose.prod.yml      # Orchestrated production setup
├── manage.py
├── pytest.ini                   # Test configuration
├── requirements.txt             # Direct dependencies
└── ruff.toml                    # Linter & formatter settings

```

---

## Quickstart & Environment Setup

### Environment Configuration

Clone the repository and copy the example environment configuration:

```bash
cp .env.example .env

```

Default configuration inside `.env`:

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

---

## Local Development (Docker Compose)

The local development setup mounts live code volumes into the containers for automatic hot-reloading when editing Django views or Celery task files.

### 1. Launch local stack

```bash
docker compose up --build -d

```

### 2. Run migrations

```bash
docker compose exec web python manage.py migrate

```

### 3. Create a superuser

```bash
docker compose exec web python manage.py createsuperuser

```

The app will be available at:

* **API Base**: `http://localhost:8000/api/`
* **Swagger Documentation**: `http://localhost:8000/api/docs/`
* **Health Probes**: `http://localhost:8000/api/health/ready/`

---

## Production Deployment

The production configuration runs Django behind Gunicorn inside a hardened container (`USER django`), proxied by Nginx for static file serving and client buffering.

### 1. Build and Run Production Services

```bash
docker compose -f docker-compose.prod.yml up --build -d

```

### 2. Collect Static Files & Apply Migrations

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate

```

Production stack handles traffic via Nginx on port `80`.

---

## API Documentation & Examples

### 1. User Registration & Authentication

**Register a User**:

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "email": "dev@example.com",
    "password": "securepassword123"
  }'

```

**Obtain JWT Bearer Token**:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "securepassword123"
  }'

```

*Response*:

```json
{
  "refresh": "eyJhbGciOi...",
  "access": "eyJhbGciOi..."
}

```

---

### 2. Idempotent Task Creation

In unstable network conditions, include an `Idempotency-Key` header. Subsequent requests bearing the same key will bypass task creation and immediately return the cached original response.

```bash
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Idempotency-Key: task-req-uuid-001" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Process Large Dataset",
    "description": "Background ingestion job"
  }'

```

*Response (`201 Created`)*:

```json
{
  "id": 1,
  "title": "Process Large Dataset",
  "description": "Background ingestion job",
  "status": "PENDING",
  "result_data": {},
  "error_message": "",
  "retry_count": 0,
  "owner": "developer",
  "created_at": "2026-10-08T14:30:00Z",
  "updated_at": "2026-10-08T14:30:00Z"
}

```

---

### 3. Fetching and Filtering Tasks

**Filter tasks by status**:

```bash
curl -X GET "http://localhost:8000/api/tasks/?status=COMPLETED&ordering=-created_at" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

```

**Search task content**:

```bash
curl -X GET "http://localhost:8000/api/tasks/?search=Dataset" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

```

---

### 4. Health Probes

* **Liveness Probe** (`GET /api/health/live/`): Verifies the application container web worker process is running. Returns `200 OK`.
* **Readiness Probe** (`GET /api/health/ready/`): Verifies database connection pool and Redis connection before directing traffic.

*Healthy Response (`200 OK`)*:

```json
{
  "status": "ok",
  "checks": {
    "postgres": "ok",
    "redis": "ok"
  }
}

```

*Degraded Response (`503 Service Unavailable`)*:

```json
{
  "status": "unavailable",
  "checks": {
    "postgres": "ok",
    "redis": "error"
  }
}

```

---

## Testing & Quality Assurance

Run the test suite, linting, and formatting checks locally or via Docker:

### Execute Pytest Suite

```bash
docker compose exec web pytest

```

### Run Linter (Ruff)

```bash
docker compose exec web ruff check .

```

### Auto-format Code

```bash
docker compose exec web ruff format .

```

---

## CI/CD Pipeline

Automated testing is configured via GitHub Actions in `.github/workflows/ci.yml`. On every pull request or push to the `main` branch, the workflow:

1. Spins up PostgreSQL and Redis service containers.
2. Installs Python dependencies.
3. Checks code style using `ruff`.
4. Executes unit, integration, and isolation tests using `pytest`.

---

## License

Distributed under the [MIT License](https://www.google.com/search?q=LICENSE).
