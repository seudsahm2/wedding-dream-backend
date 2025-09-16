from django.http import JsonResponse
import datetime

def health_check(request):
    """
    A simple health check endpoint that returns the server status and current time.
    """
    return JsonResponse({
        'status': 'ok',
        'time': datetime.datetime.now().isoformat()
    })
