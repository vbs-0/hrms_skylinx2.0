import os
import django
import sys

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.apps import apps
from django.db import models
from django.db import transaction

def get_company_from_user(user):
    try:
        if hasattr(user, 'employee_get') and user.employee_get:
            emp = user.employee_get
            if hasattr(emp, 'employee_work_info') and emp.employee_work_info:
                return emp.employee_work_info.company_id
    except Exception as e:
        pass
    return None

def backfill():
    from base.models import Company
    
    default_company = Company.objects.first()
    if not default_company:
        print("No companies found in database. Exiting.")
        return

    print(f"Default fallback company: {default_company} (ID: {default_company.id})")

    # Get all models
    all_models = apps.get_models()
    
    total_updated = 0

    with transaction.atomic():
        for model in all_models:
            # Check if model has company_id field
            try:
                field = model._meta.get_field('company_id')
                if not isinstance(field, models.ForeignKey) or field.related_model != Company:
                    continue
            except:
                continue
            
            # Found a model with company_id. 
            # We must use _base_manager to avoid any custom manager filters that might exclude NULLs 
            qs = model._base_manager.filter(company_id__isnull=True)
            count = qs.count()
            if count == 0:
                continue
                
            print(f"Found {count} records in {model.__name__} with NULL company_id. Updating...")
            
            # Update records
            updated_for_model = 0
            for record in qs:
                # Try to infer company from created_by
                company = None
                if hasattr(record, 'created_by') and record.created_by:
                    company = get_company_from_user(record.created_by)
                
                # Try to infer from user_id if it exists
                if not company and hasattr(record, 'user_id') and record.user_id:
                    company = get_company_from_user(record.user_id)
                    
                # Try to infer from employee_id if it exists
                if not company and hasattr(record, 'employee_id') and record.employee_id:
                    try:
                        if hasattr(record.employee_id, 'employee_work_info') and record.employee_id.employee_work_info:
                            company = record.employee_id.employee_work_info.company_id
                    except:
                        pass
                
                # Fallback to default
                if not company:
                    company = default_company
                
                record.company_id = company
                # Use update instead of save to avoid side effects (like signals or recursive saves)
                model._base_manager.filter(pk=record.pk).update(company_id=company)
                updated_for_model += 1
            
            print(f"Updated {updated_for_model} records in {model.__name__}.")
            total_updated += updated_for_model

    print(f"Backfill complete! Total records updated: {total_updated}")

if __name__ == "__main__":
    backfill()
