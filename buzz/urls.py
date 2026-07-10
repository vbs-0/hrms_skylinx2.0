from django.urls import path

from buzz import views

urlpatterns = [
    path("", views.buzz_page, name="buzz-page"),
]

api_urlpatterns = [
    path("directory/", views.DirectoryAPIView.as_view(), name="buzz-api-directory"),
    path(
        "directory/<int:employee_id>/",
        views.ProfileAPIView.as_view(),
        name="buzz-api-profile",
    ),
    path("conversations/", views.ConversationsAPIView.as_view(), name="buzz-api-conversations"),
    path(
        "conversations/<int:conversation_id>/messages/",
        views.MessagesAPIView.as_view(),
        name="buzz-api-messages",
    ),
    path("connections/", views.ConnectionsAPIView.as_view(), name="buzz-api-connections"),
    path(
        "messages/<int:message_id>/",
        views.MessageDetailAPIView.as_view(),
        name="buzz-api-message-detail",
    ),
    path(
        "moderation/<int:employee_id>/",
        views.ModerationAPIView.as_view(),
        name="buzz-api-moderation",
    ),
]
