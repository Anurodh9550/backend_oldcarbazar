from django.urls import path

from apps.inquiries.consumers import ExpertRequestConsumer

websocket_urlpatterns = [
    path("ws/admin/expert-requests/", ExpertRequestConsumer.as_asgi()),
]
