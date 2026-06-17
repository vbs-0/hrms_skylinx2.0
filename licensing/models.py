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

BILLING_PERIODS = [
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]


class Plan(models.Model):
    """Vendor-defined subscription plan (server role)."""

    name = models.CharField(max_length=120, unique=True)
    billing_period = models.CharField(
        max_length=10, choices=BILLING_PERIODS, default="monthly"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # blank/null = unlimited employees
    employee_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Blank = unlimited"
    )
    # list of paid-feature keys this plan unlocks (see features.PAID_FEATURES)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_billing_period_display()})"


class License(models.Model):
    """A license issued to one customer company (server role)."""

    STATUS = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]

    key = models.CharField(max_length=255, unique=True, db_index=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField(blank=True)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL)
    # snapshot of entitlements at issue time (so editing a Plan never silently
    # changes an already-sold license)
    employee_limit = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=list, blank=True)
    issued_on = models.DateField(default=timezone.localdate)
    expires_on = models.DateField(null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} — {self.key[:12]}…"

    def is_valid(self):
        if self.status != "active":
            return False
        if self.expires_on and self.expires_on < timezone.localdate():
            return False
        return True

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < timezone.localdate())


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
