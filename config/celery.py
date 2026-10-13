import os

from celery import Celery

# 1. Set the default Django settings module environment variable for Celery.
# This tells Celery where to look to find your project's configuration (settings.py).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Initialize the main Celery application instance.
# "config" is the name of your project package.
app = Celery("config")

# 3. Configure Celery using properties from Django's settings.
# The "CELERY" namespace means Celery will look for Django settings 
# that start with "CELERY_" (e.g., CELERY_BROKER_URL).
app.config_from_object("django.conf:settings", namespace="CELERY")

# 4. Automatically discover background tasks (tasks.py) 
# across all of your installed Django apps, saving you from manual registration.
app.autodiscover_tasks()