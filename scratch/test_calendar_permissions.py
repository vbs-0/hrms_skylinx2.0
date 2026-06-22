import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from employee.models import Employee
from base.models import Company
from leave.models import LeaveRequest, LeaveType
from datetime import date

# 1. Setup Client
client = Client()
User = get_user_model()

# 2. Get/Create regular test user
test_user, created = User.objects.get_or_create(username="testemployee")
if created:
    test_user.set_password("password123")
    test_user.save()

# Get or create company
company = Company.objects.first()
if not company:
    company = Company.objects.create(name="Test Company")

# Create a different employee for this user
emp_test, emp_created = Employee.objects.get_or_create(
    employee_first_name="Test",
    employee_last_name="Employee",
    email="testemp@company.com",
)
# Correctly link Employee to SkylinxUser
emp_test.employee_user_id = test_user
emp_test.save()

# Get/create LeaveType
lt = LeaveType.objects.first()
if not lt:
    lt = LeaveType.objects.create(name="Casual Leave", payment="paid")

# Create approved leave for Test Employee
lr, lr_created = LeaveRequest.objects.get_or_create(
    employee_id=emp_test,
    leave_type_id=lt,
    start_date=date(2026, 6, 28),
    end_date=date(2026, 6, 29),
    status="approved",
    requested_days=2
)

# 3. Test as Admin (Superuser)
admin_user = User.objects.get(username="admin")
client.force_login(admin_user)
url = reverse("holiday-calendar-view")
response_admin = client.get(url)
html_admin = response_admin.content.decode("utf-8")

print("--- ADMIN VIEW ---")
# The admin user should see "Admin User" leave and "Test Employee" leave
print("Admin User in Admin view:", "Admin User" in html_admin)
print("Test Employee in Admin view:", "Test Employee" in html_admin)

# 4. Test as Regular Employee
client.force_login(test_user)
response_emp = client.get(url)
html_emp = response_emp.content.decode("utf-8")

print("--- REGULAR EMPLOYEE VIEW ---")
# The regular employee should NOT see "Admin User" leave, but should see "Test Employee" leave
print("Admin User in Regular Employee view (Expected False):", "Admin User" in html_emp)
print("Test Employee in Regular Employee view (Expected True):", "Test Employee" in html_emp)
