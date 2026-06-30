import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benta.settings')

# Only import consumers if real-time tracking is enabled
try:
    from realestate import consumers
    websocket_urlpatterns = [
        path('ws/tracking/<str:user_type>/', consumers.LocationTrackingConsumer.as_asgi()),
    ]
except ImportError:
    websocket_urlpatterns = []

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})