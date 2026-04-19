"""URL configuration for the chat app."""

from django.urls import path

from apps.chat.views import ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
]
