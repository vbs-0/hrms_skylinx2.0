from django.apps import AppConfig


class BackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_backup"

    def ready(self):
        from django.urls import include, path

        from skylinx.urls import urlpatterns

        urlpatterns.append(
            path("backup/", include("skylinx_backup.urls")),
        )
        super().ready()
