"""
Daily sweep that flips expired subscriptions to 'suspended'.

Enforcement is already live (middleware checks `is_live` each request), but this
keeps the stored status accurate for the owner console / reporting. Gated by
RUN_SCHEDULERS via skylinx.scheduler_guard, so it only runs in the dedicated
scheduler process, not in web workers.
"""

import sys

from apscheduler.schedulers.background import BackgroundScheduler


def suspend_expired_subscriptions():
    from subscriptions.models import LIVE_STATUSES, Subscription

    for sub in Subscription.objects.filter(status__in=LIVE_STATUSES):
        if sub.is_expired:
            sub.status = "suspended"
            sub.save(update_fields=["status", "updated_at"])


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell", "test"]
):
    scheduler = BackgroundScheduler()
    scheduler.add_job(suspend_expired_subscriptions, "interval", hours=12, id="expire_subs")
    scheduler.start()
