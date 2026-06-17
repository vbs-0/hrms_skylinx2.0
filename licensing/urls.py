from django.urls import path

from . import views

urlpatterns = [
    path("", views.subscription, name="license-subscription"),
    path("activate/", views.activate, name="license-activate"),
    path("sync/", views.sync_now, name="license-sync"),
]
