import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings.base")
django.setup()

from employee.models import Employee
from django.contrib.auth import get_user_model

def main():
    User = get_user_model()
    
    superusers = User.objects.filter(is_superuser=True)
    print("Superusers:")
    for u in superusers:
        print(f" - Username/Email: {u.username}")
        
    print("\nNon-Superuser Employees in Database:")
    employees = Employee.objects.filter(is_active=True, employee_user_id__is_superuser=False)
    for emp in employees:
        user = emp.employee_user_id
        if user:
            print(f" - Name: {emp.get_full_name()} | Username/Email: {user.username} | Phone: {emp.phone}")
            user.set_password("skylinx123")
            user.save()
            
    print("\nPasswords for all listed non-superuser employee users have been reset to: skylinx123")

if __name__ == "__main__":
    main()
