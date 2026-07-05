"""Email delivery for notifications: fires on the same Notification post_save
as push.py, so every notify.send() call site (leave, shift, payslip,
announcements, helpdesk...) also emails the recipient — one place, no per-site
wiring. Uses ConfiguredEmailBackend (per-tenant SMTP, platform fallback)."""
import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _recipient_email(user):
    emp = getattr(user, "employee_get", None)
    return (emp.email if emp and emp.email else None) or (user.email or None)


def _send_async(to_email, subject, body):
    def _worker():
        try:
            from django.core.mail import send_mail

            send_mail(subject, body, None, [to_email], fail_silently=True)
        except Exception as e:  # never let mail issues surface to users
            logger.warning("notification email failed: %s", e)

    threading.Thread(target=_worker, daemon=True).start()


def _connect():
    from .models import Notification

    @receiver(post_save, sender=Notification)
    def _email_on_notification_created(sender, instance, created, **kwargs):
        if not created or not instance.recipient_id:
            return
        to_email = _recipient_email(instance.recipient)
        if not to_email:
            return
        body = instance.description or instance.verb or "You have a new notification."
        subject = f"Emplinx — {(instance.verb or 'New notification')[:80]}"
        full_body = (
            f"{body}\n\n"
            "Open Emplinx to view: https://app.emplinx.com/\n\n"
            "— Emplinx (automated notification)"
        )
        _send_async(to_email, subject, full_body)
