from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SkylinxAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_auth"
    verbose_name = _("Auth")
