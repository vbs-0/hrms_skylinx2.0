from django.urls import path

from . import vendor_views, views

urlpatterns = [
    # Client-side subscription dashboard
    path("", views.subscription, name="license-subscription"),
    path("activate/", views.activate, name="license-activate"),
    path("sync/", views.sync_now, name="license-sync"),
    # Vendor (server role) dashboard
    path("vendor/", vendor_views.dashboard, name="license-vendor"),
    path("vendor/plan/create/", vendor_views.plan_create, name="license-plan-create"),
    path(
        "vendor/license/generate/",
        vendor_views.license_generate,
        name="license-generate",
    ),
]
