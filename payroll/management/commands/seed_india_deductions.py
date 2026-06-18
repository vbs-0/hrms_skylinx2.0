"""
seed_india_deductions.py

Seeds the three mandatory statutory deduction components for India:
  - PF (Provident Fund)   — 12% of basic (employee share)
  - ESI (Employee State Insurance) — 0.75% of gross (employee share)
  - PT (Professional Tax) — flat amount (State-dependent, defaults to 0)

Run once per setup; safe to run again (skips existing titles).
    python manage.py seed_india_deductions
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _


DEDUCTIONS = [
    {
        "title": "Provident Fund (PF) - Employee",
        "is_tax": False,
        "is_pretax": False,
        "is_fixed": False,       # percentage-based
        "amount": 0,
        "based_on": "basic_pay",
        "rate": 12.00,           # 12% of basic
        "employer_rate": 12.00,  # employer also contributes 12%
        "is_condition_based": False,
        "include_active_employees": True,
        "update_compensation": True,
    },
    {
        "title": "Employee State Insurance (ESI) - Employee",
        "is_tax": False,
        "is_pretax": False,
        "is_fixed": False,
        "amount": 0,
        "based_on": "gross_pay",
        "rate": 0.75,            # 0.75% of gross
        "employer_rate": 3.25,   # employer pays 3.25%
        "is_condition_based": False,
        "include_active_employees": True,
        "update_compensation": True,
    },
    {
        "title": "Professional Tax (PT)",
        "is_tax": True,
        "is_pretax": False,
        "is_fixed": True,        # flat amount
        "amount": 0,             # 0 default: PT is state-dependent and must be set per company/state
        "based_on": "basic_pay",
        "rate": 0,
        "employer_rate": 0,
        "is_condition_based": False,
        "include_active_employees": True,
        "update_compensation": True,
    },
]


class Command(BaseCommand):
    help = "Seed India statutory deduction records (PF, ESI, PT)."

    def handle(self, *args, **kwargs):
        from payroll.models.models import Deduction

        created = 0
        skipped = 0

        for data in DEDUCTIONS:
            title = data["title"]
            if Deduction.objects.filter(title=title).exists():
                self.stdout.write(f"  [SKIP] Already exists: {title}")
                skipped += 1
                continue

            obj = Deduction(
                title=title,
                is_tax=data["is_tax"],
                is_pretax=data["is_pretax"],
                is_fixed=data["is_fixed"],
                amount=data["amount"],
                based_on=data.get("based_on", "basic_pay"),
                rate=data["rate"],
                employer_rate=data["employer_rate"],
                is_condition_based=data["is_condition_based"],
                include_active_employees=data["include_active_employees"],
                update_compensation=data["update_compensation"],
                is_active=True,
            )
            obj.save()
            created += 1
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {title}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone -- {created} deduction(s) created, {skipped} skipped."
        ))
