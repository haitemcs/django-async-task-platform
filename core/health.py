import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def liveness_check(request):
    return JsonResponse(
        {"status": "live", "service": "async-task-platform"},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    checks = {
        "database": "healthy",
        "cache_redis": "healthy",
    }
    is_ready = True

    try:
        connection.ensure_connection()
    except Exception:
        logger.exception("Readiness check failed: database unavailable")
        checks["database"] = "unhealthy"
        is_ready = False

    try:
        broker_url = getattr(
            settings,
            "REDIS_URL",
            getattr(
                settings,
                "CELERY_BROKER_URL",
                "redis://127.0.0.1:6379/0",
            ),
        )
        client = redis.Redis.from_url(broker_url, socket_timeout=2)
        client.ping()
    except Exception:
        logger.exception("Readiness check failed: Redis unavailable")
        checks["cache_redis"] = "unhealthy"
        is_ready = False

    return JsonResponse(
        {
            "status": "ready" if is_ready else "unhealthy",
            "checks": checks,
        },
        status=(
            status.HTTP_200_OK
            if is_ready
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
    )
