from django.urls import path

from . import views

urlpatterns = [
    # Client-side subscription dashboard
    path("subscription/", views.subscription, name="license-subscription"),
    path("sync/", views.sync_now, name="license-sync"),
]
