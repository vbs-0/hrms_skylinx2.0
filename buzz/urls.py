from django.urls import path

from buzz import views

urlpatterns = [
    path("", views.buzz_page, name="buzz-page"),
]

api_urlpatterns = [
    path("directory/", views.DirectoryAPIView.as_view(), name="buzz-api-directory"),
    path("conversations/", views.ConversationsAPIView.as_view(), name="buzz-api-conversations"),
    path(
        "conversations/<int:conversation_id>/messages/",
        views.MessagesAPIView.as_view(),
        name="buzz-api-messages",
    ),
    path("connections/", views.ConnectionsAPIView.as_view(), name="buzz-api-connections"),
]
