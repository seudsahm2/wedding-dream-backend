from django.urls import path
from .views import (
    ContactRequestCreateView,
    ThreadListView,
    ThreadDetailView,
    ThreadMessageCreateView,
    ThreadMarkReadView,
    ThreadStartView,
    ThreadMessagesListView,
)

urlpatterns = [
    path("contact", ContactRequestCreateView.as_view(), name="contact-request"),
    path("threads/start/", ThreadStartView.as_view(), name="thread-start"),
    path("threads/", ThreadListView.as_view(), name="thread-list"),
    path("threads/<int:pk>/", ThreadDetailView.as_view(), name="thread-detail"),
    path("threads/<int:pk>/messages/list/", ThreadMessagesListView.as_view(), name="thread-messages-list"),
    path("threads/<int:pk>/messages/", ThreadMessageCreateView.as_view(), name="thread-message-create"),
    path("threads/<int:pk>/read/", ThreadMarkReadView.as_view(), name="thread-mark-read"),
]
