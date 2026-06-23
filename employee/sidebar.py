"""
employee/sidebar.py

To set Skylinx sidebar for employee
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from accessibility.methods import check_is_accessible
from base.templatetags.basefilters import is_reportingmanager
from skylinx.skylinx_middlewares import _thread_locals
from skylinx.menu import settings_menu

request = getattr(_thread_locals, "request", None)
MENU = _("Employee")
IMG_SRC = "images/ui/employees.svg"


SUBMENUS = [
    {
        "menu": _("Employees"),
        "redirect": reverse_lazy("employee-view"),
        "accessibility": "employee.sidebar.employee_accessibility",
    },
    {
        "menu": _("Document Requests"),
        "redirect": reverse_lazy("document-request-view"),
        "accessibility": "employee.sidebar.document_accessibility",
    },
    {
        "menu": _("Shift Requests"),
        "redirect": reverse_lazy("shift-request-view"),
    },
    {
        "menu": _("Rotating Shift Assign"),
        "redirect": reverse_lazy("rotating-shift-assign"),
        "accessibility": "employee.sidebar.rotating_shift_accessibility",
    },
    {
        "menu": _("Shift Roster"),
        "redirect": reverse_lazy("roster-home"),
        "accessibility": "employee.sidebar.shift_roster_accessibility",
    },
    {
        "menu": _("Disciplinary Actions"),
        "redirect": reverse_lazy("disciplinary-actions"),
    },
    {
        "menu": _("Policies"),
        "redirect": reverse_lazy("view-policies"),
    },
    {
        "menu": _("Organization Chart"),
        "redirect": reverse_lazy("organisation-chart"),
    },
]



def document_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "skylinx_documents.view_documentrequest"
    ) or is_reportingmanager(request.user)


def rotating_shift_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingshiftassign"
    ) or is_reportingmanager(request.user)


def rotating_work_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingworktypeassign"
    ) or is_reportingmanager(request.user)


def shift_roster_accessibility(request, submenu, user_perms, *args, **kwargs):
    return False


def employee_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Employee accessibility method restricted to superusers, managers, or view_employee permission.
    """
    return (
        request.user.is_superuser
        or is_reportingmanager(request.user)
        or request.user.has_perm("employee.view_employee")
    )


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def work_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_worktype")


def rotating_work_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_rotatingworktype")


def employee_shift_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_employeeshift")


def rotating_shift_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_rotatingshift")


def shift_schedule_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_employeeshiftschedule")


def employee_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_employeetype")


def disciplinary_action_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("employee.view_actiontype")


def employee_tag_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("employee.view_employeetag")


@settings_menu.register
class EmployeeSettings:
    title = _("Employee")
    order = 3
    items = [
        {
            "label": _("Work Type"),
            "url": reverse_lazy("work-type-view"),
            "accessibility": work_type_accessibility,
        },
        {
            "label": _("Rotating Work Type"),
            "url": reverse_lazy("rotating-work-type-view"),
            "accessibility": rotating_work_type_accessibility,
        },
        {
            "label": _("Employee Shift"),
            "url": reverse_lazy("employee-shift-view"),
            "accessibility": employee_shift_accessibility,
        },
        {
            "label": _("Rotating Shift"),
            "url": reverse_lazy("rotating-shift-view"),
            "accessibility": rotating_shift_accessibility,
        },
        {
            "label": _("Employee Shift Schedule"),
            "url": reverse_lazy("employee-shift-schedule-view"),
            "accessibility": shift_schedule_accessibility,
        },
        {
            "label": _("Employee Type"),
            "url": reverse_lazy("employee-type-view"),
            "accessibility": employee_type_accessibility,
        },
        {
            "label": _("Disciplinary Action Type"),
            "url": reverse_lazy("action-type"),
            "accessibility": disciplinary_action_accessibility,
        },
        {
            "label": _("Employee Tags"),
            "url": reverse_lazy("employee-tag-view"),
            "accessibility": employee_tag_accessibility,
        },
    ]
