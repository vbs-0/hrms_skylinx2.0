"""
Suspend subscriptions whose term has ended.

Run on a schedule (e.g. daily cron):
    python manage.py expire_subscriptions

The middleware already blocks expired subs at request time via `is_live`; this
flips their stored status to `suspended` so the owner console reflects reality
and clients see an accurate state.
"""

from django.core.management.base import BaseCommand

from subscriptions.models import LIVE_STATUSES, Subscription


class Command(BaseCommand):
    help = "Mark expired (trial/active) subscriptions as suspended."

    def handle(self, *args, **options):
        suspended = 0
        for sub in Subscription.objects.filter(status__in=LIVE_STATUSES):
            if sub.is_expired:
                sub.status = "suspended"
                sub.save(update_fields=["status", "updated_at"])
                suspended += 1
                self.stdout.write(f"Suspended: {sub.company} ({sub.plan or 'no plan'})")
        self.stdout.write(self.style.SUCCESS(f"Done. {suspended} subscription(s) suspended."))
