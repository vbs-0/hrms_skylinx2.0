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
    # `price` is the MONTHLY price; `yearly_price` is the (optional) annual price
    # shown when the client toggles to yearly billing. 0 yearly_price => no yearly
    # option offered for this tier (e.g. the free plan).
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    # per-company feature overrides: keys here are enabled regardless of plan
    feature_overrides = models.JSONField(default=list, blank=True)
    # per-company seat limit override (null = use plan.seat_limit)
    seat_override = models.PositiveIntegerField(null=True, blank=True)
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
        if self.seat_override is not None:
            return self.seat_override
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
        if key in (self.feature_overrides or []):
            return True
        return key in self.feature_keys()


class AISettings(models.Model):
    """Platform-wide AI assistant config — owner-managed on /manage.

    One row (singleton). The key never reaches the browser: the chat endpoint
    proxies server-side. Works with any OpenAI-compatible API (Groq, Mistral,
    OpenRouter, self-hosted Ollama).
    """

    enabled = models.BooleanField(default=False)
    api_base = models.CharField(
        max_length=255, default="https://api.groq.com/openai/v1"
    )
    api_key = models.CharField(max_length=255, blank=True, default="")
    model_name = models.CharField(
        max_length=120, default="llama-3.3-70b-versatile"
    )
    # role gates: who inside every tenant may use the assistant
    allow_employee = models.BooleanField(default=True)
    allow_hr = models.BooleanField(default=True)
    allow_ceo = models.BooleanField(default=True)

    ACTION_LEVEL_CHOICES = [
        ("guidance", "Guidance only — explains, never touches data"),
        ("suggest", "Suggest + human confirms — proposes an action, a person must click confirm"),
        ("execute", "AI executes directly — can approve/reject pending leave requests on instruction; everything else stays Suggest"),
    ]
    # Platform-wide ceiling: no company can grant its AI more capability than
    # this, even if the company admin picks a higher option in their own
    # settings. Set here on /manage, chosen per-company under company settings.
    max_action_level = models.CharField(
        max_length=20, choices=ACTION_LEVEL_CHOICES, default="guidance"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SupportSettings(models.Model):
    """Platform-wide support-desk config — owner-managed on /manage.
    Singleton, same pattern as AISettings."""

    forward_email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Support notification email",
        help_text=(
            "Every new support ticket is emailed here, sent via whichever "
            "mail server the raising company/its fallback primary is "
            "configured with. Leave blank to rely on in-app notifications only."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Support Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
    ]

    company = models.ForeignKey(
        "base.Company", on_delete=models.CASCADE, related_name="support_tickets"
    )
    raised_by = models.ForeignKey(
        "employee.Employee", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=3000)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.company}] {self.subject}"
