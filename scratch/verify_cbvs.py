import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")

import django
django.setup()

import inspect

from leave.cbv.assigned_leave import AssignedLeaveNavView
from leave.cbv.leave_allocation_request import LeaveAllocationRequestNav
from leave.cbv.my_leave_request import MyLeaveRequestNavView
from payroll.cbv.payslip import PayslipNav
from leave.cbv.leave_requests import LeaveRequestsNavView
from attendance.cbv.attendances import AttendancesNavView
from attendance.cbv.attendance_request import AttendanceRequestNav
from skylinx_views.generic.cbv.views import SkylinxNavView
from base.views import holiday_calendar_view

checks = [
    ("SkylinxNavView has create_label attr", hasattr(SkylinxNavView, "create_label")),
    ("SkylinxNavView.create_label default is empty string", SkylinxNavView.create_label == ""),
    ("LeaveRequestsNavView disables create", 'self.create_attrs = ""' in inspect.getsource(LeaveRequestsNavView.__init__)),
    ("AssignedLeaveNavView label=Assign", "Assign" in inspect.getsource(AssignedLeaveNavView.__init__)),
    ("LeaveAllocationRequestNav label=Request", "Request" in inspect.getsource(LeaveAllocationRequestNav.__init__)),
    ("MyLeaveRequestNavView label=Apply", "Apply" in inspect.getsource(MyLeaveRequestNavView.__init__)),
    ("PayslipNav label=Generate", "Generate" in inspect.getsource(PayslipNav.__init__)),
    ("AttendancesNavView disables create", 'self.create_attrs = ""' in inspect.getsource(AttendancesNavView.__init__)),
    ("AttendanceRequestNav disables create", 'self.create_attrs = ""' in inspect.getsource(AttendanceRequestNav.__init__)),
    ("holiday_calendar_view is callable", callable(holiday_calendar_view)),
]

all_pass = True
for name, ok in checks:
    status = "OK  " if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {name}")

print()
print("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED")
