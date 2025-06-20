"""
ASGI config for test_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_project.settings')

django_asgi_app = get_asgi_application()

import sample_app.routing
import uno_game.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            sample_app.routing.websocket_urlpatterns +
            uno_game.routing.websocket_urlpatterns
        )
    ),
})
