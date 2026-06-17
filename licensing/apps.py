from django.apps import AppConfig


class LicensingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "licensing"

    def ready(self):
        from django.urls import include, path

        from skylinx.urls import urlpatterns

        from . import api

        urlpatterns.append(
            path("license/", include("licensing.urls")),
        )
        # Vendor verify endpoint clients sync against (server role).
        urlpatterns.append(
            path("api/license/verify", api.verify, name="license-verify"),
        )
        from . import signals  # noqa: F401  (register employee-cap enforcement)

        super().ready()
