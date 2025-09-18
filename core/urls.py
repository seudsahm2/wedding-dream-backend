from django.urls import path
from .views import health_check, celery_health

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('health/celery/', celery_health, name='celery_health'),
]
