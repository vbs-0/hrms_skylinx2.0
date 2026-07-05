from django.urls import path

from . import views
from . import ai_assistant

urlpatterns = [
    path("", views.console, name="subscriptions-console"),
    path("analytics/", views.console_analytics, name="subscriptions-analytics"),
    path("ai-settings/", views.ai_settings, name="subscriptions-ai-settings"),
    path("ai-chat/", ai_assistant.ai_chat, name="ai-chat"),
    path("ai-company-settings/", views.company_ai_settings, name="subscriptions-company-ai-settings"),
    path("onboard/", views.onboard, name="subscriptions-onboard"),
    path(
        "company/<int:company_id>/update/",
        views.subscription_update,
        name="subscriptions-update",
    ),
    path("impersonate/<int:user_id>/", views.impersonate, name="subscriptions-impersonate"),
    path("stop-impersonate/", views.stop_impersonate, name="subscriptions-stop-impersonate"),
    path("plans/", views.plans_list, name="subscriptions-plans"),
    path("plans/new/", views.plan_edit, name="subscriptions-plan-new"),
    path("plans/<int:plan_id>/edit/", views.plan_edit, name="subscriptions-plan-edit"),
    path("plans/<int:plan_id>/delete/", views.plan_delete, name="subscriptions-plan-delete"),
]
