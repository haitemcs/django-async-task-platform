# admin: Imports Django's built-in, ready-to-use administrative web interface site.
from django.contrib.admin import admin

# include: Allows taking a group of URL patterns from another file and linking them here.
# path: Maps a specific URL string URL pattern to a view, router, or included URL file.
from django.urls import include, path


# This is the master traffic controller (root url configuration) for the entire Django project.
# Incoming requests hit this file first before being handed off to specific app-level URL files.
urlpatterns = [
    # path("admin/"): 
    # Mounts Django's built-in administration dashboard at the /admin/ URL. 
    # This gives developers a secure UI out-of-the-box to manage database records, users, and models.
    path("admin/", admin.site.urls),

    # path("health/"): 
    # Delegates all URLs starting with /health/ to the core app's URL configuration (core.urls).
    # This is where your liveness and readiness probe endpoints (like /health/live/ or /health/ready/) live, 
    # allowing orchestration tools (like Docker or Kubernetes) to monitor app health.
    path("health/", include("core.urls")),

    # path("api/"): 
    # Delegates all URL traffic starting with /api/ to your tasks app's URL configuration (tasks/urls.py).
    # Because of this, everything built in your DefaultRouter (like task CRUD routes and user registration) 
    # will cleanly sit behind the /api/ prefix (e.g., /api/tasks/, /api/register/, /api/auth/token/).
    path("api/", include("tasks.urls")),
]