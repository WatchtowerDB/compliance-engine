import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watchtower_ce.settings")

# Create a Celery application instance
app = Celery("watchtower_ce")

# Load Celery configuration from Django settings, using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks from all installed Django apps
app.autodiscover_tasks()
