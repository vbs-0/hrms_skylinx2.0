import json

from django import template
from django.apps import apps
from django.core.paginator import Page, Paginator
from django.template.defaultfilters import register

from base.methods import get_pagination
from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from skylinx.menu.settings_menu import get_settings_menu

register = template.Library()


@register.filter
def equals(value, arg):
    """Check if value equals arg"""
    return value == arg


@register.simple_tag
def is_manager_of(user, instance, field_name="employee_id"):
    employee = Employee.objects.filter(employee_user_id=user).first()

    target_employee = getattr(instance, field_name, None)

    return EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee, employee_id=target_employee
    ).exists()


@register.filter(name="is_reportingmanager")
def is_reportingmanager(user):
    """

    This method will return true if the user employee profile is reporting manager to any employee
    """
    if not user or user.is_anonymous:
        return False
    if not hasattr(user, "_is_reporting_manager_cached"):
        employee = getattr(user, "employee_get", None)
        if not employee:
            user._is_reporting_manager_cached = False
        else:
            user._is_reporting_manager_cached = EmployeeWorkInformation.objects.filter(
                reporting_manager_id=employee
            ).exists()
    return user._is_reporting_manager_cached


@register.filter(name="is_leave_approval_manager")
def is_leave_approval_manager(user):
    """
    This method will return true if the user is comes in MultipleApprovalCondition model as approving manager
    """
    if not user or user.is_anonymous:
        return False
    if not hasattr(user, "_is_leave_approval_manager_cached"):
        employee = getattr(user, "employee_get", None)
        if not employee:
            user._is_leave_approval_manager_cached = False
        else:
            user._is_leave_approval_manager_cached = (
                MultipleApprovalManagers.objects.entire()
                .filter(employee_id=employee.id)
                .exists()
            )
    return user._is_leave_approval_manager_cached


@register.filter(name="check_manager")
def check_manager(user, instance):
    try:
        employee = getattr(user, "employee_get", None)
        if not employee:
            return False
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == employee
        return (
            employee
            == instance.employee_id.employee_work_info.reporting_manager_id
        )
    except:
        return False


@register.filter(name="filtersubordinates")
def filtersubordinates(user):
    """
    This method returns true if the user employee has corresponding related reporting manager object in EmployeeWorkInformation model
    args:
        user    : request.user
    """
    if not user or user.is_anonymous:
        return False
    if not hasattr(user, "_filtersubordinates_cached"):
        employee = getattr(user, "employee_get", None)
        if not employee:
            user._filtersubordinates_cached = False
        else:
            user._filtersubordinates_cached = employee.reporting_manager.exists()
    return user._filtersubordinates_cached


@register.filter(name="filter_field")
def filter_field(value):
    if value.endswith("_id"):
        value = value[:-3]
    if value.endswith("_ids"):
        value = value[:-4]
    splitted = value.split("__")

    return splitted[-1].replace("_", " ").capitalize()


@register.filter(name="user_perms")
def user_perms(perms):
    """
    permission names return method
    """
    perms_list = [f"{p['content_type__app_label']}.{p['codename']}" for p in perms.values("content_type__app_label", "codename")]
    return json.dumps(perms_list)


@register.filter(name="abs_value")
def abs_value(value):
    """
    permission names return method
    """
    return abs(value)


@register.filter(name="config_perms")
def config_perms(user):
    if not user or not user.is_authenticated:
        return False

    # 1. Multiple Approvals
    if apps.is_installed("leave") and user.has_perm("base.view_multipleapprovalcondition"):
        return True

    # 2. Mail Templates
    if user.has_perm("base.view_skylinxmailtemplate") or user.has_perm("base.view_skylinxmailtemplates"):
        return True

    # 3. Mail Automations
    if apps.is_installed("skylinx_automations") and user.has_perm("skylinx_automations.view_mailautomation"):
        return True

    # 4. Holidays
    if user.has_perm("base.add_holidays") or user.has_perm("base.add_holiday"):
        return True

    # 5. Company Leaves
    if user.has_perm("base.view_companyleaves"):
        return True

    # 6. Google Meet (requires skylinx_meet app and integration installed, plus permission)
    if apps.is_installed("skylinx_meet"):
        try:
            from base.models import IntegrationApps
            if IntegrationApps.objects.filter(app_label="skylinx_meet", is_enabled=True).exists() and user.has_perm("skylinx_meet.view_googlemeeting"):
                return True
        except Exception:
            pass

    return False


@register.filter(name="startswith")
def startswith(value, arg):
    """Checks if the value starts with the provided argument."""
    return value.startswith(arg)


@register.filter(name="has_content")
def has_content(value):
    """Returns True if the input string has non-whitespace content."""
    if isinstance(value, str):
        return bool(value.strip())
    return True


@register.filter(name="readable")
def readable(value):
    try:
        value = value.replace("_", " ").replace("id", "").title()
    except:
        value = value
    return value


@register.simple_tag(takes_context=True)
def general_section_main(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("skylinx_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("base.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("skylinx_audit.view_audittag"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("skylinx_backup.view_googledrivebackup"),
        ]
    )


@register.simple_tag(takes_context=True)
def general_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("skylinx_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("base.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
        ]
    )


@register.simple_tag(takes_context=True)
def employee_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("employee.view_employeetag"),
        ]
    )


@register.simple_tag(takes_context=True)
def attendance_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
        ]
    )


@register.simple_tag(takes_context=True)
def show_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("helpdesk.view_departmentmanager"),
            user.has_perm("helpdesk.view_tickettype"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("pms.add_bonuspointsetting"),
            user.has_perm("payroll.view_payslipautogenerate"),
            user.has_perm("leave.add_restrictleave"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
            user.has_perm("recruitment.view_recruitment"),
            user.has_perm("recruitment.view_rejectreason"),
            user.has_perm("recruitment.add_recruitment"),
            user.has_perm("recruitment.add_linkedinaccount"),
            user.has_perm("skylinx_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("skylinx_audit.view_audittag"),
            user.has_perm("skylinx_backup.view_googledrivebackup"),
            user.has_perm("skylinx_ldap.add_ldapsettings"),
            user.has_perm("skylinx_ldap.update_ldapsettings"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("helpdesk.view_tag"),
            user.has_perm("whatsapp.view_whatsappcredentials"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("base.view_department"),
            user.has_perm("base.view_jobposition"),
            user.has_perm("base.view_jobrole"),
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("skylinx_backup.view_googledrivebackup"),
            user.has_perm("recruitment.view_linkedinaccount"),
            user.has_perm("skylinx_ldap.add_ldapsettings"),
            user.has_perm("skylinx_ldap.update_ldapsettings"),
            user.has_perm("skylinx_meet.view_googlecloudcredential"),
            user.has_perm("whatsapp.add_whatsappcredentials"),
            user.has_perm("skylinx_theme.view_skylinxcolortheme"),
        ]
    )


@register.simple_tag(takes_context=True)
def settings_menu(context):

    request = context.get("request")
    if request is None:
        return []
    return get_settings_menu(request)
