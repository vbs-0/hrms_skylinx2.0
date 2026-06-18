"""
seed_direct_hire_recruitment.py

Creates a hidden "Direct Hire" Recruitment sentinel record for every active
Company. This allows HR to onboard walk-in / referral hires without going
through the full ATS pipeline.

Usage:
    python manage.py seed_direct_hire_recruitment
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _


from onboarding.constants import DIRECT_HIRE_TITLE


class Command(BaseCommand):
    help = "Seed a hidden Direct Hire recruitment record for each company."

    def handle(self, *args, **kwargs):
        from base.models import Company
        from recruitment.models import Recruitment

        companies = Company.objects.all()
        created = 0
        for company in companies:
            obj, was_created = Recruitment.objects.get_or_create(
                title=DIRECT_HIRE_TITLE,
                company_id=company,
                defaults={
                    "description": "System-managed: Direct Hire / Walk-in path",
                    "is_active": False,   # hidden from normal recruitment listings
                    "closed": True,
                    "is_published": False,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] Created Direct Hire record for company: {company}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {created} new Direct Hire record(s) created "
            f"({companies.count() - created} already existed)."
        ))
