from django.contrib.auth import get_user_model
from django.db import connection
from django.db import transaction
from django.http import JsonResponse
from django_redis import get_redis_connection

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Task
from .serializers import RegisterSerializer, TaskSerializer
from .tasks import process_task


User = get_user_model()


class RegisterViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    filterset_fields = ["status"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Task.objects.filter(
            owner=self.request.user
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            task = serializer.save(owner=self.request.user)

            transaction.on_commit(
                lambda: process_task.delay(task.id)
            )


@api_view(["GET"])
@permission_classes([AllowAny])
def live_health(request):
    return JsonResponse(
        {
            "status": "ok",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def ready_health(request):
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        redis = get_redis_connection("default")
        redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    healthy = all(
        value == "ok"
        for value in checks.values()
    )

    return JsonResponse(
        {
            "status": "ok" if healthy else "unavailable",
            "checks": checks,
        },
        status=200 if healthy else 503,
    )

