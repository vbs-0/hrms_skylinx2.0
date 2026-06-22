import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails

print("Employee fields:")
for f in Employee._meta.get_fields():
    if not f.is_relation or f.many_to_one:
        print(f"  {f.name}: {type(f).__name__}")

print("\nEmployeeWorkInformation fields:")
for f in EmployeeWorkInformation._meta.get_fields():
    if not f.is_relation or f.many_to_one:
        print(f"  {f.name}: {type(f).__name__}")

print("\nEmployeeBankDetails fields:")
for f in EmployeeBankDetails._meta.get_fields():
    if not f.is_relation or f.many_to_one:
        print(f"  {f.name}: {type(f).__name__}")
