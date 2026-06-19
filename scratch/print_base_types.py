import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from base.models import WorkType, EmployeeType, EmployeeShift

print("Work Types:")
for wt in WorkType.objects.all():
    print(f"  ID: {wt.id}, Name: {wt.work_type}")

print("\nEmployee Types:")
for et in EmployeeType.objects.all():
    print(f"  ID: {et.id}, Name: {et.employee_type}")

print("\nEmployee Shifts:")
for es in EmployeeShift.objects.all():
    print(f"  ID: {es.id}, Name: {es.employee_shift}")
