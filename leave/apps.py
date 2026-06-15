from django.apps import AppConfig, apps


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leave"

    def ready(self):
        from django.urls import include, path

        from skylinx.skylinx_settings import APPS
        from skylinx.urls import urlpatterns
        from leave import signals

        APPS.append("leave")
        urlpatterns.append(
            path("leave/", include("leave.urls")),
        )
        super().ready()
