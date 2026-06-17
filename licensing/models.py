"""
Licensing models.

Two roles share these tables (selected by settings.LICENSE_ROLE):

  server  — the vendor's private instance. Manages Plan + License: define
            subscription plans, generate keys, track issued licenses, expiry,
            discounts and revenue.
  client  — a deployed HRMS. Reads its own entitlements from the LicenseConfig
            singleton (populated by the sync command from the server).
"""

from django.db import models
from django.utils import timezone



class LicenseConfig(models.Model):
    """
    Client-side singleton (pk=1): the active license key and the entitlements
    last synced from the vendor server. Enforcement reads only this row.
    """

    license_key = models.CharField(max_length=255, blank=True)
    plan_name = models.CharField(max_length=120, blank=True)
    employee_limit = models.PositiveIntegerField(null=True, blank=True)
    enabled_features = models.JSONField(default=list, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="active")
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "License configuration"
        verbose_name_plural = "License configuration"

    def __str__(self):
        return self.plan_name or self.license_key or "Unlicensed"

    @classmethod
    def get(cls):
        obj = cls.objects.filter(pk=1).first()
        if not obj:
            obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < timezone.localdate())

    @property
    def days_remaining(self):
        if not self.expires_on:
            return None
        return (self.expires_on - timezone.localdate()).days
