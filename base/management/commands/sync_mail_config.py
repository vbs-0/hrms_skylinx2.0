"""
Repair / sync the primary DynamicEmailConfiguration from .env SMTP_* settings.

The DB mail config drives password reset, invites and notifications. If its
username/password drift from the working .env creds (e.g. a truncated Gmail
username), mail silently fails. This rewrites the primary row to match settings.

    python manage.py sync_mail_config
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from base.models import DynamicEmailConfiguration


class Command(BaseCommand):
    help = "Sync the primary mail-server config row from .env (SMTP_*) settings."

    def handle(self, *args, **opts):
        host = getattr(settings, "EMAIL_HOST", None)
        user = getattr(settings, "EMAIL_HOST_USER", None)
        if not host or not user:
            self.stdout.write(self.style.ERROR("EMAIL_HOST / EMAIL_HOST_USER not set in .env."))
            return

        cfg = DynamicEmailConfiguration.objects.filter(is_primary=True).first()
        if cfg is None:
            cfg = DynamicEmailConfiguration(is_primary=True)

        cfg.host = host
        cfg.port = getattr(settings, "EMAIL_PORT", 587)
        cfg.username = user
        cfg.password = getattr(settings, "EMAIL_HOST_PASSWORD", "")
        cfg.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", user)
        cfg.use_tls = getattr(settings, "EMAIL_USE_TLS", True)
        cfg.use_ssl = getattr(settings, "EMAIL_USE_SSL", False)
        cfg.fail_silently = False
        if not cfg.display_name:
            cfg.display_name = "EMPLINX"
        cfg.save()

        self.stdout.write(self.style.SUCCESS(f"Primary mail config synced: {user}@{host}:{cfg.port}"))
