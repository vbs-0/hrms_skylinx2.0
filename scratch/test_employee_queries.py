import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from employee.models import Employee

qs = Employee.objects.select_related(
    "employee_work_info",
    "employee_work_info__department_id",
    "employee_work_info__job_position_id",
    "employee_work_info__job_position_id__department_id",
)

# Print the SQL query
print("Query SQL:")
print(qs.query)

# Let's fetch one employee and check if job_position_id.department_id triggers a query
print("Employee count:", Employee.objects.count())

from base.models import JobPosition
print("JobPosition count:", JobPosition.objects.count())
for jp in JobPosition.objects.all():
    print("JobPosition:", jp)

