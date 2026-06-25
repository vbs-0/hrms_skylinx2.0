"""
Bootstrap the subscription layer:

  * create the default Plans (Free, Starter, Pro, Enterprise)
  * give every existing Company an active subscription (so nothing locks out
    after the migration)

Idempotent: safe to run repeatedly.

    python manage.py seed_subscriptions
"""

from django.core.management.base import BaseCommand

from base.models import Company

from subscriptions.features import ALL_FEATURE_KEYS
from subscriptions.models import Plan, Subscription

DEFAULT_PLANS = [
    # name, slug, price, cycle, seat_limit, features
    ("Free", "free", 0, "trial", 5, []),
    ("Starter", "starter", 999, "monthly", 25, ["payroll", "recruitment"]),
    (
        "Pro",
        "pro",
        2999,
        "monthly",
        100,
        ["payroll", "recruitment", "pms", "asset", "helpdesk"],
    ),
    ("Enterprise", "enterprise", 7999, "monthly", None, ALL_FEATURE_KEYS),
]


class Command(BaseCommand):
    help = "Create default plans and give every company an active subscription."

    def handle(self, *args, **options):
        plans = {}
        for name, slug, price, cycle, seats, feats in DEFAULT_PLANS:
            plan, _ = Plan.objects.update_or_create(
                slug=slug,
                defaults=dict(
                    name=name,
                    price=price,
                    billing_cycle=cycle,
                    seat_limit=seats,
                    features=feats,
                    is_active=True,
                ),
            )
            plans[slug] = plan
        self.stdout.write(self.style.SUCCESS(f"Plans ready: {', '.join(plans)}"))

        # default existing companies to Enterprise+active so they keep full access
        enterprise = plans["enterprise"]
        created = 0
        for company in Company.objects.all():
            sub, was_created = Subscription.objects.get_or_create(
                company=company,
                defaults=dict(plan=enterprise, status="active"),
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Subscriptions: {created} created, "
                f"{Subscription.objects.count()} total."
            )
        )
