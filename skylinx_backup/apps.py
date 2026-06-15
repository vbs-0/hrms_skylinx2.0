from django.apps import AppConfig


class BackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_backup"

    def ready(self):
        from django.urls import include, path

        from skylinx.urls import urlpatterns
        from skylinx_backup import views

        urlpatterns.append(
            path("backup/", include("skylinx_backup.urls")),
        )
        # Add root-level callback URL to match OAuth redirect URI
        urlpatterns.append(
            path(
                "google/callback/", views.gdrive_callback, name="gdrive_callback_root"
            ),
        )
        super().ready()
