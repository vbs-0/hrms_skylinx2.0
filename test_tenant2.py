import os
import django
import traceback
import uuid
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from subscriptions.views import create_tenant
from base.models import Company
from skylinx.skylinx_middlewares import _thread_locals
from django.db.models.signals import post_save
from employee.models import Employee, BonusPoint

# Replace the bonus_post_save to add print statements
original_bonus_post_save = None
for receiver in post_save._live_receivers(Employee):
    if receiver.__name__ == 'bonus_post_save':
        original_bonus_post_save = receiver

call_count = 0

def debug_bonus_post_save(sender, instance, **_kwargs):
    global call_count
    call_count += 1
    print(f"DEBUG: bonus_post_save called {call_count} times for {instance}")
    if not BonusPoint.objects.filter(employee_id__id=instance.id).exists():
        print(f"DEBUG: BonusPoint does not exist for {instance.id}. Creating...")
        try:
            BonusPoint.objects.create(employee_id=instance)
            print("DEBUG: BonusPoint created.")
        except Exception as e:
            print("DEBUG: Exception creating BonusPoint:")
            traceback.print_exc(file=sys.stdout)
    else:
        print(f"DEBUG: BonusPoint already exists for {instance.id}")

post_save.disconnect(receiver=original_bonus_post_save, sender=Employee)
post_save.connect(debug_bonus_post_save, sender=Employee)

class MockRequest:
    def __init__(self, user):
        self.user = user
        self.scheme = 'http'
        
    def get_host(self):
        return 'localhost:8000'

def run():
    try:
        from skylinx_auth.models import SkylinxUser as User
        owner_company = Company.objects.first()
        owner_user = Employee.objects.filter(employee_work_info__company_id=owner_company).first().employee_user_id
        
        req = MockRequest(owner_user)
        _thread_locals.request = req
        
        uid = str(uuid.uuid4())[:8]
        company_name = f"TestCompany_{uid}"
        username = f"admin_{uid}"
        email = f"test_{uid}@test.com"
        
        create_tenant(company_name, username, email, "pass", None)
        print("Success!")
    except Exception as e:
        print("Error:")
        traceback.print_exc()
    finally:
        _thread_locals.request = None

if __name__ == "__main__":
    run()
