from django.urls import path

from . import views

urlpatterns = [
    path("", views.console, name="subscriptions-console"),
    path("onboard/", views.onboard, name="subscriptions-onboard"),
    path(
        "company/<int:company_id>/update/",
        views.subscription_update,
        name="subscriptions-update",
    ),
    path("impersonate/<int:user_id>/", views.impersonate, name="subscriptions-impersonate"),
    path("stop-impersonate/", views.stop_impersonate, name="subscriptions-stop-impersonate"),
]
