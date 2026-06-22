import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from leave.models import LeaveRequest
qs = LeaveRequest.objects.all()
print(f"Total leaves: {qs.count()}")
print(f"Approved leaves: {qs.filter(status='approved').count()}")
for l in qs.filter(status='approved')[:10]:
    print(f"ID: {l.id}, Employee: {l.employee_id}, Start: {l.start_date}, End: {l.end_date}, Status: {l.status}")
