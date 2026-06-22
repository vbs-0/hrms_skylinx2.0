import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.contrib.auth import get_user_model
from employee.models import Employee
from base.models import Holidays
from leave.models import LeaveRequest
from django.apps import apps

User = get_user_model()

# Delete seeded leave requests
lr_deleted, _ = LeaveRequest.objects.filter(employee_id__employee_first_name="Test").delete()
print(f"Deleted test employee leaves: {lr_deleted}")

# Find and delete admin test leave request
lr_admin_deleted, _ = LeaveRequest.objects.filter(employee_id__employee_first_name="Admin User", start_date__year=2026).delete()
print(f"Deleted admin test leaves: {lr_admin_deleted}")

# Delete seeded holidays
h_deleted, _ = Holidays.objects.filter(name="Midsummer Holiday").delete()
print(f"Deleted holidays: {h_deleted}")

# Find test employees
test_emps = Employee.objects.filter(employee_first_name="Test")

# Delete referencing Contracts dynamically
try:
    Contract = apps.get_model("payroll", "Contract")
    contracts_deleted, _ = Contract.objects.filter(employee_id__in=test_emps).delete()
    print(f"Deleted test employee contracts: {contracts_deleted}")
except Exception as e:
    print(f"Contract model check failed/skipped: {e}")

# Delete referencing EmployeeWorkInformation dynamically if needed
try:
    EmployeeWorkInformation = apps.get_model("employee", "EmployeeWorkInformation")
    work_info_deleted, _ = EmployeeWorkInformation.objects.filter(employee_id__in=test_emps).delete()
    print(f"Deleted test employee work info: {work_info_deleted}")
except Exception as e:
    print(f"Work Info model check failed/skipped: {e}")

# Delete test employee profiles
emp_deleted, _ = test_emps.delete()
print(f"Deleted test employee profiles: {emp_deleted}")

# Delete test user
user_deleted, _ = User.objects.filter(username="testemployee").delete()
print(f"Deleted test users: {user_deleted}")
