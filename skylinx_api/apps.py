from django.apps import AppConfig


class SkylinxApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_api"

    def ready(self):
        """
        Initialize API documentation when the app is ready
        """
        # Import and register API documentation components
        import skylinx_api.schema  # noqa
