"""
ASGI config for wedding_dream project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from typing import Any, cast
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wedding_dream.settings.dev")

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.urls import re_path
    from messaging.auth import JWTAuthMiddleware
    from messaging.ws import ChatConsumer
except ImportError:
    # Fallback if channels is not installed
    application = django_asgi_app
else:
    websocket_urlpatterns: list[Any] = [
        # Pylance/mypy may not understand ASGI consumers here; cast to Any.
        re_path(r"^ws/threads/(?P<pk>\\d+)/$", cast(Any, ChatConsumer.as_asgi())),
    ]

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    })
