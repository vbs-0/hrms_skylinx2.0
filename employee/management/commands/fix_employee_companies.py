"""
Backfill company-less employee work-info rows.

A work-info row with company_id = NULL leaks the employee into EVERY tenant's
list (the company manager treats NULL as 'visible everywhere'). This stamps all
such rows onto a target company so multi-tenant isolation holds.

    python manage.py fix_employee_companies            # dry-run, lists count
    python manage.py fix_employee_companies --apply     # assign to HQ company
    python manage.py fix_employee_companies --apply --company-id 3
"""

from django.core.management.base import BaseCommand

from base.models import Company
from employee.models import EmployeeWorkInformation


class Command(BaseCommand):
    help = "Assign company-less employee work-info rows to a company (HQ by default)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually write changes.")
        parser.add_argument("--company-id", type=int, default=None, help="Target company id (default: HQ).")

    def handle(self, *args, **opts):
        orphans = EmployeeWorkInformation.objects.entire().filter(company_id__isnull=True)
        count = orphans.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No company-less employees. Nothing to do."))
            return

        if opts["company_id"]:
            target = Company.objects.filter(id=opts["company_id"]).first()
        else:
            target = Company.objects.filter(hq=True).first() or Company.objects.order_by("id").first()

        if not target:
            self.stdout.write(self.style.ERROR("No target company found. Pass --company-id."))
            return

        self.stdout.write(f"{count} company-less work-info row(s) -> '{target}' (id={target.id})")
        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("Dry-run. Re-run with --apply to write."))
            return

        updated = orphans.update(company_id=target)
        self.stdout.write(self.style.SUCCESS(f"Assigned {updated} employee(s) to '{target}'."))
