import os
from celery import Celery

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wedding_dream.settings.dev")

app = Celery("wedding_dream")

# Load config from Django settings with CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def ping(self):  # simple health task
    return "pong"
