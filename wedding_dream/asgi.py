"""
ASGI config for wedding_dream project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wedding_dream.settings")

django_asgi_app = get_asgi_application()

try:
	from channels.routing import ProtocolTypeRouter, URLRouter
	from messaging.auth import JWTAuthMiddleware
	from django.urls import path
	from messaging.ws import ChatConsumer

	application = ProtocolTypeRouter({
		"http": django_asgi_app,
		"websocket": JWTAuthMiddleware(
			URLRouter([
				path("ws/threads/<int:pk>/", ChatConsumer.as_asgi()),
			])
		),
	})
except Exception:
	# Fallback if channels not installed/misconfigured
	application = django_asgi_app
