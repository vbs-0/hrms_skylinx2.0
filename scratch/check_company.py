import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from base.models import Company, Department, JobPosition, JobRole
from employee.models import Employee

print("Companies:")
for c in Company.objects.all():
    print(f"  ID: {c.id}, Name: {c.company}")

print("\nDepartments:")
for d in Department.objects.all():
    print(f"  ID: {d.id}, Name: {d.department}")

print("\nJob Positions:")
for jp in JobPosition.objects.all():
    print(f"  ID: {jp.id}, Name: {jp.job_position}")

print("\nJob Roles:")
for jr in JobRole.objects.all():
    print(f"  ID: {jr.id}, Name: {jr.job_role}")

print("\nEmployees:")
for e in Employee.objects.all():
    print(f"  ID: {e.id}, Name: {e.employee_first_name} {e.employee_last_name}, Active: {e.is_active}")
