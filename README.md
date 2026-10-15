# Async Task Processing Platform

A containerized Django REST API for submitting asynchronous tasks, tracking their lifecycle, and storing processing results. The project is built to practice backend engineering concepts including REST APIs, JWT authentication, PostgreSQL persistence, Celery workers, Redis, health checks, and Docker Compose.

> **Status: work in progress.** The core application structure and local Compose environment are in place. Automated test coverage is currently minimal, and idempotency, retry/recovery behavior, and production hardening still need additional work. This is a learning and portfolio project, not a production-ready service.

## Contents

- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Features](#features)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Health checks](#health-checks)
- [Testing and development checks](#testing-and-development-checks)
- [Known limitations and roadmap](#known-limitations-and-roadmap)
- [Stopping the environment](#stopping-the-environment)
- [License](#license)

## Architecture

The application separates HTTP requests from background processing:

```text
                         ┌──────────────────┐
Client ── HTTP ─────────▶│ Nginx (8080)      │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │ Django + Gunicorn│
                         │ REST API         │
                         └──────┬─────┬─────┘
                                │     │
                       persist  │     │ enqueue
                                ▼     ▼
                         ┌──────────┐ ┌──────────────┐
                         │PostgreSQL│ │ Redis        │
                         │ task data│ │ Celery broker│
                         └──────────┘ └──────┬───────┘
                                              ▼
                                      ┌──────────────┐
                                      │ Celery worker│
                                      └──────┬───────┘
                                             │
                                             ▼
                                      Update task state
                                      and persist result
```

Task submissions are intended to be dispatched after the database transaction commits. PostgreSQL stores task records and results; Redis is used as the Celery broker and result backend.

## Technology stack

- **Language:** Python 3.12
- **Web framework:** Django 6.1.2
- **API:** Django REST Framework 3.18.3
- **Authentication:** JSON Web Tokens with Simple JWT
- **Background jobs:** Celery 5.6.3
- **Database:** PostgreSQL 15
- **Broker/cache:** Redis 7
- **Reverse proxy:** Nginx
- **Application server:** Gunicorn
- **API utilities:** django-filter, drf-spectacular
- **Local environment:** Docker Compose

Dependency versions are pinned in `requirements.txt`; service images are configured in `docker-compose.yml`.

## Features

- REST endpoints for registering users and managing tasks
- JWT access and refresh token endpoints
- Owner-scoped task querysets
- Task lifecycle states: `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED`
- Task metadata including title, description, result data, error details, retry count, and timestamps
- Celery background processing with retry configuration
- PostgreSQL persistence and task-related database indexes
- Liveness and readiness endpoints
- Docker Compose services for the API, PostgreSQL, Redis, Celery worker, and Nginx
- Django REST Framework configuration for pagination, filtering, search, ordering, and throttling

**Important:** configuration being present does not mean every feature is fully tested. See [Known limitations and roadmap](#known-limitations-and-roadmap).

## Project structure

```text
django-async-task-platform/
├── config/                 # Django settings, root URLs, WSGI/ASGI, Celery setup
├── core/                   # Health checks and middleware
├── tasks/                  # Task API, models, serializers, and Celery task
├── docker/
│   └── nginx.conf          # Nginx reverse-proxy configuration
├── scripts/
│   └── entrypoint.sh       # Database startup helper
├── .env.example            # Example environment configuration
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
├── requirements.txt
├── LICENSE
└── README.md
```

## Getting started

### Prerequisites

Install the following:

- Docker Engine
- Docker Compose v2 (the `docker compose` command)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/haitemcs/django-async-task-platform.git
cd django-async-task-platform
```

### 2. Configure environment variables

Create a local environment file if you need to override the Compose defaults:

```bash
cp .env.example .env
```

Review `.env.example` and adjust values for local development. Never commit `.env` or real credentials.

### 3. Build and start the services

```bash
docker compose up --build -d
```

Check the service state and logs:

```bash
docker compose ps
docker compose logs --tail=100 web celery_worker db redis nginx
```

### 4. Apply database migrations

```bash
docker compose exec web python manage.py migrate
```

### 5. Check the Django configuration

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

### 6. Open the local endpoints

The current Compose port mappings are:

| Service | Local address / port | Purpose |
|---|---|---|
| Nginx | http://localhost:8080/ | Reverse proxy |
| Django/Gunicorn | http://localhost:8000/ | Direct API access |
| Liveness | http://localhost:8080/health/live/ | Confirms the app process responds |
| Readiness | http://localhost:8080/health/ready/ | Checks database and Redis dependencies |
| PostgreSQL | `localhost:5433` | Local database connection |
| Redis | `localhost:6379` | Local Redis connection |

Health routes are mounted under `/health/`, not `/api/`. The readiness endpoint should return an unsuccessful status when a required dependency is unavailable.

PostgreSQL's initialization variables create the configured database and role when its data directory is first initialized. Changing values in `.env` does not automatically change credentials inside an existing persistent database volume.

## Configuration

Common environment variables include:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic secret |
| `DJANGO_DEBUG` | Enables or disables Django debug mode |
| `ALLOWED_HOSTS` | Hosts allowed by Django |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_HOST` | Database hostname inside Compose |
| `POSTGRES_PORT` | Database port inside Compose |
| `REDIS_URL` | Redis connection URL |
| `CELERY_BROKER_URL` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | Celery result backend URL |

Use the values and variable names in `.env.example` as the source of truth for the current implementation. Any fallback credentials are for local development only. Before deployment, require a strong secret key, disable debug mode, configure allowed hosts and HTTPS settings, and review which service ports should be publicly exposed.

## API reference

Unless otherwise stated, API routes are prefixed with `/api/`.

### Authentication and registration

| Method | Endpoint | Purpose | Authentication |
|---|---|---|---|
| `POST` | `/api/register/` | Create a user account | Public |
| `POST` | `/api/auth/token/` | Obtain JWT access and refresh tokens | Public |
| `POST` | `/api/auth/token/refresh/` | Obtain a new access token from a refresh token | Refresh token |

Example registration request:

```bash
curl -X POST http://localhost:8080/api/register/ \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "demo_user",
    "email": "demo@example.com",
    "password": "change-this-password"
  }'
```

Obtain a token pair:

```bash
curl -X POST http://localhost:8080/api/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "demo_user",
    "password": "change-this-password"
  }'
```

Use the returned access token for protected endpoints:

```bash
-H 'Authorization: Bearer <access-token>'
```

### Task endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/tasks/` | List the authenticated user's tasks |
| `POST` | `/api/tasks/` | Submit a task |
| `GET` | `/api/tasks/{id}/` | Retrieve a task |
| `PUT` / `PATCH` | `/api/tasks/{id}/` | Update an accessible task |
| `DELETE` | `/api/tasks/{id}/` | Delete an accessible task |

Task requests require authentication. The API is designed to scope task queries to the current user so that one user cannot access another user's tasks.

Example task submission:

```bash
curl -X POST http://localhost:8080/api/tasks/ \
  -H 'Authorization: Bearer <access-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Example background task",
    "description": "Submitted from the REST API"
  }'
```

A task moves through the lifecycle states `PENDING`, `PROCESSING`, `COMPLETED`, or `FAILED`. The current Celery workload is a demonstration implementation; it is not yet a general-purpose job execution engine.

Filtering, search, ordering, and pagination are configured in the API. Check the current view and settings configuration for the supported query parameters. Interactive Swagger/Redoc routes are not currently exposed in the root URL configuration.

## Health checks

- `GET /health/live/` — checks whether the application responds.
- `GET /health/ready/` — checks whether required dependencies, including PostgreSQL and Redis, are reachable.

Use the readiness endpoint when diagnosing a local environment. Avoid exposing detailed internal exception messages from health checks in a public production deployment.

## Testing and development checks

Run the current automated tests inside the web container:

```bash
docker compose exec web pytest
```

You can also run Django's test runner:

```bash
docker compose exec web python manage.py test
```

**Current test coverage is incomplete.** The existing test modules include placeholder coverage, so a green test result does not establish that authentication, task ownership, Celery processing, retries, or idempotency work correctly.

Before considering a change complete, run the configuration checks above and add behavioral tests for the feature being changed. Recommended coverage includes:

- Registration validation and JWT authentication
- Anonymous access rejection
- Task creation, listing, updating, and deletion
- Cross-user task isolation
- Celery dispatch and result persistence
- Retry and terminal failure behavior
- Liveness/readiness responses when dependencies fail
- Idempotency behavior, including concurrent duplicate submissions

## Known limitations and roadmap

The project is intentionally being developed in stages. The main remaining work is:

- [ ] Replace placeholder tests with meaningful API and integration tests
- [ ] Review and harden idempotency handling, including user/operation scoping and concurrent requests
- [ ] Verify Celery retry behavior and add recovery for tasks left in a processing state after a worker failure
- [ ] Improve reliability when a task is committed to the database but cannot be published to the broker
- [ ] Add CI for checks, tests, linting, and Docker image builds
- [ ] Harden production settings, container permissions, and exposed service ports
- [ ] Expose generated OpenAPI schema and interactive API documentation
- [ ] Replace the demonstration task workload with a meaningful processing use case
- [ ] Add operational logging, metrics, and task monitoring

Do not treat the current Compose setup as a production deployment without addressing these items.

## Stopping the environment

Stop the containers while preserving the PostgreSQL data volume:

```bash
docker compose down
```

To also delete the persistent PostgreSQL volume, you can use `docker compose down -v`, but **this permanently deletes the database data stored in that volume**. Only do so when you intentionally want a clean local database.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
