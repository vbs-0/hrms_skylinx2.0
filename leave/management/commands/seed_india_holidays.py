"""
seed_india_holidays.py

Seeds the mandatory national holidays for India.
Run once per setup; safe to run again (skips existing dates for the year).
    python manage.py seed_india_holidays
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _


HOLIDAYS = [
    {
        "name": "Republic Day",
        "month": 1,
        "day": 26,
    },
    {
        "name": "Independence Day",
        "month": 8,
        "day": 15,
    },
    {
        "name": "Gandhi Jayanti",
        "month": 10,
        "day": 2,
    },
]


class Command(BaseCommand):
    help = "Seed India National Holidays (Republic Day, Independence Day, Gandhi Jayanti)."

    def handle(self, *args, **kwargs):
        from leave.models import Holiday
        from base.models import Company

        created = 0
        skipped = 0
        current_year = date.today().year

        companies = Company.objects.all()

        if not companies.exists():
            self.stdout.write(self.style.WARNING("No companies found. Skipping holiday seeding."))
            return

        for company in companies:
            for data in HOLIDAYS:
                holiday_date = date(current_year, data["month"], data["day"])
                
                # Check if holiday exists for this date and company
                if Holiday.objects.filter(start_date=holiday_date, company_id=company).exists():
                    self.stdout.write(f"  [SKIP] Already exists for {company}: {data['name']} ({holiday_date})")
                    skipped += 1
                    continue

                obj = Holiday(
                    name=data["name"],
                    start_date=holiday_date,
                    end_date=holiday_date,
                    recurring=True,
                    company_id=company,
                    is_active=True,
                )
                obj.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created for {company}: {data['name']} ({holiday_date})"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone -- {created} holiday(s) created, {skipped} skipped."
        ))
