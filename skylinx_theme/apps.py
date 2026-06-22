"""
AppConfig for the skylinx_theme app
"""

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SkylinxThemeConfig(AppConfig):
    """App configuration class for skylinx_theme."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_theme"
    verbose_name = _("Theme Manager")

    def ready(self):
        """Run app initialization logic (executed after Django setup).
        Used to auto-register URLs and connect signals if required.
        """
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from skylinx.urls import urlpatterns

            settings.APPS.append(("skylinx_theme"))
            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("theme/", include("skylinx_theme.urls")),
            )

            __import__("skylinx_theme.signals")
        except Exception as e:
            import logging

            logging.warning("SkylinxThemeConfig.ready failed: %s", e)

        super().ready()
