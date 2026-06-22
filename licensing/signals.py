"""
Employee cap enforcement (client role, hard block).

Blocks any save that would push the active-employee count past the licensed
limit — a brand-new active employee, or re-enabling a disabled one. Updates to
already-active employees never add to the count, so they pass through.

Fail-open: unlicensed / server role / no cap => employee_limit is None and this
is a no-op.
"""

from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender="employee.Employee")
def enforce_employee_cap(sender, instance, **kwargs):
    if not instance.is_active:
        return  # disabled employees never count

    from . import service

    limit = service.employee_limit()
    if limit is None:
        return

    # Would this save increase the active count?
    adds_one = True
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values_list(
            "is_active", flat=True
        ).first()
        if previous:  # already active -> no increase
            adds_one = False

    if adds_one and service.active_employee_count() >= limit:
        raise PermissionDenied(
            "License limit reached: your plan allows %s active employees. "
            "Upgrade your subscription to add more." % limit
        )
