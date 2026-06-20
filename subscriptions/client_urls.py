"""Client-facing pages (under /subscription/ — exempt from enforcement)."""

from django.urls import path

from . import views

urlpatterns = [
    path("inactive/", views.subscription_inactive, name="subscription-inactive"),
    path("locked/", views.feature_locked, name="feature-locked"),
    path("stop-impersonate/", views.stop_impersonate, name="subscription-stop-impersonate"),
]
