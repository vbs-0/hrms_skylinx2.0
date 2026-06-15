from django.apps import AppConfig
from django.conf import settings


class SkylinxMeetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_meet"
    verbose_name = "Skylinx Meet"

    def ready(self):
        from django.urls import include, path

        from skylinx.urls import urlpatterns
        from skylinx_meet import signals

        settings.APPS.append("skylinx_meet")

        urlpatterns.append(
            path("meet/", include("skylinx_meet.urls")),
        )
        super().ready()
