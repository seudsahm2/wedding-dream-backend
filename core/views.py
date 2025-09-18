from django.http import JsonResponse
import datetime
from wedding_dream.celery import app as celery_app
from kombu.exceptions import OperationalError as KombuOperationalError  # type: ignore[import-not-found]

def health_check(_request):
    """
    A simple health check endpoint that returns the server status and current time.
    """
    return JsonResponse({
        'status': 'ok',
        'time': datetime.datetime.now().isoformat()
    })


def celery_health(_request):
    """Lightweight Celery health check.

    Returns number of responding workers using control.ping().
    """
    try:
        replies = celery_app.control.ping(timeout=0.5)  # list of {hostname: 'pong'}
        workers = len(replies) if replies else 0
        return JsonResponse({"ok": workers > 0, "workers": workers})
    except (TimeoutError, OSError, ConnectionError, KombuOperationalError) as exc:
        return JsonResponse({"ok": False, "workers": 0, "error": str(exc)}, status=503)
