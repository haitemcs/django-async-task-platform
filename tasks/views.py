from django.contrib.auth import get_user_model
from django.db import connection, transaction
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
    # We use GenericViewSet here instead of ModelViewSet because account creation 
    # is a single action (POST). We don't want a full list/update/delete interface for registration.
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request):
        # Grab raw request data, pass it to the registration serializer.
        serializer = self.get_serializer(data=request.data)
        
        # Validate input (e.g. check if passwords match, username is unique).
        # raise_exception=True tells DRF to automatically return a 400 Bad Request if validation fails.
        serializer.is_valid(raise_exception=True)
        
        # Save the user to the database. The serializer/user model handles hashing the password 
        # behind the scenes so we never save plain-text passwords.
        user = serializer.save()

        # Return a clean dictionary response with a 201 Created status code.
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class TaskViewSet(viewsets.ModelViewSet):
    # ModelViewSet automatically gives us full CRUD (List, Retrieve, Create, Update, Destroy).
    serializer_class = TaskSerializer

    # Built-in filtering options for API query parameters:
    filterset_fields = ["status"]                  # e.g., /api/tasks/?status=pending
    search_fields = ["title", "description"]       # e.g., /api/tasks/?search=report
    ordering_fields = ["created_at", "updated_at"] # fields clients can sort by
    ordering = ["-created_at"]                     # default sort: newest tasks first

    def get_queryset(self):
        # CRITICAL SECURITY RULE (IDOR Prevention):
        # By default, ModelViewSet queries all rows in the database table. 
        # We override this method so every single query is strictly filtered 
        # to only return tasks owned by the currently authenticated user.
        return Task.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # We override perform_create to handle database transactions and background queues safely.
        # with transaction.atomic(): opens a database transaction block. If an error occurs 
        # anywhere inside this block, Django rolls back the database changes so we don't save half-baked data.
        with transaction.atomic():
            # Force the owner to be the logged-in user. Even if a malicious client 
            # tries to pass a different owner ID in the JSON body, the server overrides it here.
            task = serializer.save(owner=self.request.user)

            # CRITICAL BACKEND PATTERN (Race Condition Prevention):
            # We call transaction.on_commit() to delay triggering the Celery background worker 
            # until PostgreSQL has completely written and committed the task row to disk. 
            # If we didn't do this, the background worker might pick up the job instantly, 
            # query the database, and throw a "Task does not exist" error because the main 
            # thread hasn't finished saving it yet.
            transaction.on_commit(
                lambda: process_task.delay(task.id)
            )


@api_view(["GET"])
@permission_classes([AllowAny])
def live_health(request):
    # LIVENESS PROBE: Used by orchestration tools like Docker or Kubernetes. 
    # It simply checks if the Python/Django web server process is alive and responding to requests.
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def ready_health(request):
    # READINESS PROBE: Goes a step further than liveness. It actively pings 
    # all critical infrastructure dependencies to verify the app is fully operational.
    checks = {}

    # Test 1: Can we talk to the PostgreSQL database?
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")  # Light raw query to check DB responsiveness
            cursor.fetchone()
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    # Test 2: Can we talk to the Redis cache/broker?
    try:
        redis = get_redis_connection("default")
        redis.ping()  # Sends a ping command to Redis
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # The app is only healthy if EVERY dependency check returned "ok".
    healthy = all(v == "ok" for v in checks.values())

    # Return 200 OK if everything is working, or 503 Service Unavailable if a dependency is down.
    return JsonResponse(
        {
            "status": "ok" if healthy else "unavailable",
            "checks": checks,
        },
        status=200 if healthy else 503,
    )