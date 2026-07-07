"""
v1 mirror of the notifications API for the Flutter app.

The original routes (notifications/urls.py) only ever existed at the API
root (/api/notifications/notifications/...), never under /api/v1/ - the
only prefix the app's ApiService uses. Every call the app made 404'd.
Same views, just exposed under v1 with the trailing-slash convention
ApiService.get()/post() always produce.
"""

from django.urls import path

from ...api_views.notifications import views

urlpatterns = [
    path("list/<str:type>/", views.NotificationView.as_view()),
    path("bulk-delete-unread/", views.NotificationBulkDelUnreadMessageView.as_view()),
    path("bulk-read/", views.NotificationBulkReadDelView.as_view()),
    path("bulk-delete/", views.NotificationBulkReadDelView.as_view()),
    path("<int:id>/", views.NotificationReadDelView.as_view()),
]
