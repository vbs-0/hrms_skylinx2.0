from django.apps import AppConfig


class LicensingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "licensing"

    def ready(self):
        from django.urls import include, path

        from skylinx.urls import urlpatterns

        urlpatterns.append(
            path("license/", include("licensing.urls")),
        )
        from . import signals  # noqa: F401  (register employee-cap enforcement)

        super().ready()
