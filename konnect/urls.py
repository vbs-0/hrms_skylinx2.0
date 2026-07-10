from django.urls import path

from konnect import views

urlpatterns = [
    path("", views.konnect_page, name="konnect-page"),
]

api_urlpatterns = [
    path("feed/", views.FeedAPIView.as_view(), name="konnect-api-feed"),
    path("posts/<int:post_id>/", views.PostDetailAPIView.as_view(), name="konnect-api-post"),
    path("posts/<int:post_id>/like/", views.LikeAPIView.as_view(), name="konnect-api-like"),
    path("posts/<int:post_id>/comments/", views.CommentsAPIView.as_view(), name="konnect-api-comments"),
    path("comments/<int:comment_id>/", views.CommentDetailAPIView.as_view(), name="konnect-api-comment"),
]
