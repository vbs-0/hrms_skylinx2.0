from django.urls import path

from . import views

urlpatterns = [
    path("company-profile/", views.profile, name="company-profile"),
    path("company-profile/address/", views.addresses, name="company-profile-address"),
    path("company-profile/admin/", views.admin_onboarding, name="company-profile-admin"),
]
