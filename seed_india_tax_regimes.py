import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket
import math

def seed_tax_regimes():
    print("Seeding Tax Regimes...")
    
    # Create or get Old Regime
    old_regime, created = FilingStatus.objects.get_or_create(
        filing_status="Old Regime",
        defaults={
            "based_on": "taxable_gross_pay",
            "description": "Old Tax Regime (Pre-2020) with 80C/HRA deductions"
        }
    )
    if created:
        print("Created 'Old Regime'")
    else:
        print("'Old Regime' already exists")

    # Create or get New Regime
    new_regime, created = FilingStatus.objects.get_or_create(
        filing_status="New Regime",
        defaults={
            "based_on": "gross_pay",
            "description": "New Tax Regime (Default) - FY25-26"
        }
    )
    if created:
        print("Created 'New Regime'")
    else:
        print("'New Regime' already exists")

    # Seed Slabs for New Regime
    # India FY 2025-26 slabs:
    # 0 to 4,00,000 : 0%
    # 4,00,001 to 8,00,000 : 5%
    # 8,00,001 to 12,00,000 : 10%
    # 12,00,001 to 16,00,000 : 15%
    # 16,00,001 to 20,00,000 : 20%
    # 20,00,001 to 24,00,000 : 25%
    # 24,00,001 to infinity : 30%

    slabs = [
        (0, 400000, 0.0),
        (400001, 800000, 5.0),
        (800001, 1200000, 10.0),
        (1200001, 1600000, 15.0),
        (1600001, 2000000, 20.0),
        (2000001, 2400000, 25.0),
        (2400001, math.inf, 30.0),
    ]

    for min_inc, max_inc, rate in slabs:
        bracket, b_created = TaxBracket.objects.get_or_create(
            filing_status_id=new_regime,
            min_income=min_inc,
            defaults={
                "max_income": max_inc,
                "tax_rate": rate
            }
        )
        if b_created:
            print(f"Created Slab: {min_inc} to {max_inc} @ {rate}%")
        else:
            # update in case it was created with different values
            bracket.max_income = max_inc
            bracket.tax_rate = rate
            bracket.save()
            print(f"Updated Slab: {min_inc} to {max_inc} @ {rate}%")
            
    print("Tax regime seeding completed successfully.")

if __name__ == '__main__':
    seed_tax_regimes()
