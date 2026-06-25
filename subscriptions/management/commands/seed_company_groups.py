"""
Seed the default per-company roles (HR Manager / Manager / Employee) for every
company that doesn't have them yet. New companies get these automatically on
creation; this backfills companies that predate that.

    python manage.py seed_company_groups
"""

from django.core.management.base import BaseCommand

from base.models import Company
from subscriptions.views import _company_admin_group, seed_company_groups


class Command(BaseCommand):
    help = "Seed/refresh default per-company user groups for all existing companies."

    def handle(self, *args, **opts):
        total = 0
        for company in Company.objects.all():
            # additive & self-healing: refreshes baseline perms every run
            n = seed_company_groups(company)
            if n:
                self.stdout.write(f"  {company}: +{n} role(s)")
            total += n
        # refresh the global Company Admin group's perms too (self-heals new apps)
        admin_group = _company_admin_group()
        self.stdout.write(
            f"  Company Admin: {admin_group.permissions.count()} perms"
        )
        self.stdout.write(self.style.SUCCESS(f"Done. Seeded {total} role(s) across all companies."))
