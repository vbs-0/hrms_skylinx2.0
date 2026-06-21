"""
Multi-tenant subscription models.

Tenant = Company (base.Company). Each company has exactly one Subscription,
which points at a Plan. The Plan carries the feature list + seat cap; the
Subscription carries status + dates. Enforcement (middleware) and the sidebar
read these to lock/unlock modules per company.

This replaces the old per-deployment `licensing` app: instead of one license
key for the whole install, every company (client) has its own subscription.
"""

from django.db import models
from django.utils import timezone

from base.models import Company

from .features import ALL_FEATURE_KEYS

BILLING_CYCLES = [
    ("trial", "Trial"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]

STATUS_CHOICES = [
    ("trial", "Trial"),
    ("active", "Active"),
    ("past_due", "Past due"),
    ("suspended", "Suspended"),
    ("cancelled", "Cancelled"),
]

# statuses that grant access to the product
LIVE_STATUSES = {"trial", "active"}


class Plan(models.Model):
    """A subscription tier: price, seat cap and which modules it unlocks."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_cycle = models.CharField(
        max_length=10, choices=BILLING_CYCLES, default="monthly"
    )
    # null seat_limit => unlimited
    seat_limit = models.PositiveIntegerField(null=True, blank=True)
    # free-trial length in days when a company starts on this plan (owner-editable)
    trial_days = models.PositiveIntegerField(default=14)
    # list of feature keys from features.PAID_FEATURES that this plan unlocks
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return self.name

    def has_feature(self, key):
        return key in (self.features or [])


class Subscription(models.Model):
    """One per company. The source of truth for what a client can access."""

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions"
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="active")
    trial_ends_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company} - {self.plan or 'no plan'} ({self.status})"

    @property
    def is_expired(self):
        if self.expires_on and self.expires_on < timezone.now().date():
            return True
        if self.status == "trial" and self.trial_ends_on:
            return self.trial_ends_on < timezone.now().date()
        return False

    @property
    def is_live(self):
        """True when the company may use the product."""
        return self.status in LIVE_STATUSES and not self.is_expired

    def feature_keys(self):
        return list(self.plan.features) if self.plan else []

    @property
    def seat_limit(self):
        return self.plan.seat_limit if self.plan else None

    def seats_used(self):
        # active employees in this company = seats consumed
        from employee.models import Employee

        return Employee.objects.filter(
            is_active=True, employee_work_info__company_id=self.company
        ).count()

    def seats_available(self):
        if self.seat_limit is None:
            return None  # unlimited
        return max(0, self.seat_limit - self.seats_used())

    def has_feature(self, key):
        return key in self.feature_keys()
