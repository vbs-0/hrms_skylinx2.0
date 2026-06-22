"""URL routes for the skylinx_audit app."""

from django.urls import path

from skylinx_audit import views

urlpatterns = [
    path(
        "settings/audit-tracking/",
        views.audit_model_settings,
        name="audit-model-settings",
    ),
    path(
        "settings/audit-tracking/save/",
        views.save_audit_models,
        name="audit-model-settings-save",
    ),
    path(
        "settings/audit-tracking/<int:pk>/fields/",
        views.edit_audit_model_fields,
        name="audit-model-fields-edit",
    ),
    path(
        "audit/activity-log/",
        views.activity_log,
        name="audit-activity-log",
    ),
]
