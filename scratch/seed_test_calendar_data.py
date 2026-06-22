import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from employee.models import Employee
from base.models import Holidays, Company
from leave.models import LeaveRequest, LeaveType
from datetime import date

# Get or create company
company = Company.objects.first()
if not company:
    company = Company.objects.create(name="Test Company")

# Find an employee
emp = Employee.objects.first()
print(f"Employee: {emp}")

# Get or create a LeaveType
lt = LeaveType.objects.first()
if not lt:
    lt = LeaveType.objects.create(name="Casual Leave", payment="paid")
print(f"Leave Type: {lt}")

# Create Holiday
h, created_h = Holidays.objects.get_or_create(
    name="Midsummer Holiday",
    start_date=date(2026, 6, 24),
    end_date=date(2026, 6, 24),
    company_id=company
)
print(f"Holiday: {h}, Created: {created_h}")

# Create LeaveRequest if employee exists
if emp:
    lr, created_lr = LeaveRequest.objects.get_or_create(
        employee_id=emp,
        leave_type_id=lt,
        start_date=date(2026, 6, 25),
        end_date=date(2026, 6, 26),
        status="approved",
        requested_days=2
    )
    print(f"LeaveRequest: {lr}, Created: {created_lr}")
else:
    print("No employee found to create a leave request.")
