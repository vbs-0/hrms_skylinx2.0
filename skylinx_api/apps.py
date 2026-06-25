from django.apps import AppConfig
from django.conf import settings


class SkylinxApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_api"

    verbose_name = "API"

    def ready(self):
        """
        Initialize API documentation and configure Swagger when the app is ready.
        This method:
        1. Adds API URLs to the main project's urlpatterns
        2. Configures Swagger settings
        3. Imports schema components for auto-discovery
        """
        # Import here to avoid circular imports
        from django.urls import include, path

        from skylinx.urls import urlpatterns

        # Add API URLs to main project urlpatterns
        urlpatterns.append(
            path("api/", include("skylinx_api.urls")),
        )

        # Configure Swagger settings
        self._configure_swagger_settings()

        # Import and register API documentation components
        import skylinx_api.schema  # noqa

        super().ready()

    def _configure_swagger_settings(self):
        """
        Configure Swagger settings in Django settings.
        Merges with existing SWAGGER_SETTINGS if present.
        """
        swagger_config = {
            "SECURITY_DEFINITIONS": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "description": 'JWT Token Authentication: Enter your token with the "Bearer " prefix, e.g. "Bearer abcde12345"',
                }
            },
            "USE_SESSION_AUTH": False,
            "DEFAULT_UI_SETTINGS": {
                # Keep tag order as defined in the generated spec
                "tagsSorter": "none"
            },
            "SECURITY_REQUIREMENTS": [{"Bearer": []}],
            "DEFAULT_SCHEMA_CLASS": "skylinx_api.schema.ModuleTaggingAutoSchema",
        }

        # Merge with existing SWAGGER_SETTINGS if present
        if hasattr(settings, "SWAGGER_SETTINGS"):
            # Update existing settings, preserving any custom configurations
            if isinstance(settings.SWAGGER_SETTINGS, dict):
                settings.SWAGGER_SETTINGS.update(swagger_config)
            else:
                setattr(settings, "SWAGGER_SETTINGS", swagger_config)
        else:
            setattr(settings, "SWAGGER_SETTINGS", swagger_config)
