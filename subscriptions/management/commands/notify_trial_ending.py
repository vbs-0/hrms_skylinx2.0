"""
Email a reminder to companies whose trial ends soon (gap #7).

Run daily (alongside expire_subscriptions):
    python manage.py notify_trial_ending

Needs SMTP configured (gap #3); uses the project's configured mail backend.
Sends to the company's admin user email. Idempotent enough for a daily cron:
only fires on the exact day-counts in REMIND_DAYS so a sub gets ~3 reminders,
not one every day.
"""

from datetime import timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Subscription

REMIND_DAYS = {7, 3, 1}  # days-before-end on which to send


class Command(BaseCommand):
    help = "Email companies whose trial ends in 7/3/1 days."

    def handle(self, *args, **options):
        today = timezone.now().date()
        sent = 0
        for sub in Subscription.objects.filter(status="trial").select_related("company"):
            if not sub.trial_ends_on:
                continue
            days_left = (sub.trial_ends_on - today).days
            if days_left not in REMIND_DAYS:
                continue
            email = self._admin_email(sub.company)
            if not email:
                continue
            try:
                send_mail(
                    subject=f"Your trial ends in {days_left} day(s)",
                    message=(
                        f"Hi {sub.company},\n\n"
                        f"Your free trial ends in {days_left} day(s). "
                        f"Pick a plan to keep your account active.\n\n"
                        f"— EMPLINX"
                    ),
                    from_email=None,  # backend default
                    recipient_list=[email],
                    fail_silently=False,
                )
                sent += 1
                self.stdout.write(f"Reminded {sub.company} ({days_left}d) -> {email}")
            except Exception as e:  # SMTP not set / send failure — log, keep going
                self.stderr.write(f"Failed for {sub.company}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Done. {sent} reminder(s) sent."))

    @staticmethod
    def _admin_email(company):
        from employee.models import Employee

        emp = (
            Employee.objects.filter(employee_work_info__company_id=company)
            .exclude(email="")
            .order_by("id")
            .first()
        )
        return emp.email if emp else None
