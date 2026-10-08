import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status


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
    health_status = {
        "status": "ready",
        "checks": {
            "database": "unknown",
            "cache_redis": "unknown",
        },
    }
    is_ready = True

    try:
        connection.ensure_connection()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        is_ready = False

    try:
        broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        r = redis.Redis.from_url(broker_url, socket_timeout=2)
        if r.ping():
            health_status["checks"]["cache_redis"] = "healthy"
        else:
            health_status["checks"]["cache_redis"] = "unhealthy: ping failed"
            is_ready = False
    except Exception as e:
        health_status["checks"]["cache_redis"] = f"unhealthy: {str(e)}"
        is_ready = False

    http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    if not is_ready:
        health_status["status"] = "unhealthy"

    return JsonResponse(health_status, status=http_status)
