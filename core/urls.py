from django.urls import path
from core.health import liveness_check, readiness_check

urlpatterns = [
    path("health/live/", liveness_check, name="health-live"),
    path("health/ready/", readiness_check, name="health-ready"),
]
