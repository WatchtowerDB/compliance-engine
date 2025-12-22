import os
from celery import Celery

"""
Set default Django settings module
"""
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "watchtower_ce.settings"
)

"""
Create Celery app instance
"""
app = Celery("watchtower_ce")

""" 
Load settings from Django settings.py, prefix CELERY_

"""
app.config_from_object("django.conf:settings", namespace="CELERY")

"""
Autodiscover tasks from installed apps
"""
app.autodiscover_tasks()
