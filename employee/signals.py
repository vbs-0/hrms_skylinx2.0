from django.db.models.signals import post_save
from django.dispatch import receiver

from employee.models import Employee


@receiver(post_save, sender=Employee)
def send_welcome_mail(sender, instance, created, **kwargs):
    if not created:
        return
    from base.celebration_mail import send_celebration_mail

    send_celebration_mail(
        instance,
        subject=f"Welcome to the team, {instance.get_full_name()}!",
        heading=f"Welcome, {instance.get_full_name()}!",
        message=(
            "We're thrilled to have you on board. Your EMPLINX account is ready — "
            "log in to view your profile, mark attendance, and apply for leave."
        ),
        emoji="👋",
    )
