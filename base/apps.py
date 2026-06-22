"""
This module contains the configuration for the 'base' app.
"""

from django.apps import AppConfig, apps
from django.conf import settings


class BaseConfig(AppConfig):
    """
    Configuration class for the 'base' app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "base"

    def ready(self) -> None:
        from base import sidebar, signals  # noqa: F401

        super().ready()
        check_for_no_permissions_models()

        # Show tenant-scoped group names without their `c<id>::` storage prefix.
        from django.contrib.auth.models import Group

        from base.rbac import strip_name

        Group.add_to_class("__str__", lambda self: strip_name(self.name))
        Group.add_to_class(
            "display_name", property(lambda self: strip_name(self.name))
        )


def check_for_no_permissions_models():

    model_names = set()
    for model in apps.get_models():
        if getattr(model, "_no_permission_model", False):
            model_names.add(model._meta.model_name)

    settings.NO_PERMISSION_MODALS.extend(list(model_names))
