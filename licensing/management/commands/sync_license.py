"""
Refresh entitlements from the vendor license server.

Run on a schedule (cron / django_apscheduler) so expiry, upgrades and
revocations propagate without manual action:

    python manage.py sync_license
"""

from django.core.management.base import BaseCommand

from licensing.sync import sync_license


class Command(BaseCommand):
    help = "Sync this instance's license entitlements from the vendor server."

    def handle(self, *args, **options):
        ok, msg = sync_license()
        self.stdout.write((self.style.SUCCESS if ok else self.style.ERROR)(msg))
