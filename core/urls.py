from django.urls import path

from core.health import liveness_check, readiness_check


urlpatterns = [
    path("live/", liveness_check, name="health-live"),
    path("ready/", readiness_check, name="health-ready"),
]
