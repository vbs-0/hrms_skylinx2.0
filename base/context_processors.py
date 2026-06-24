"""
context_processor.py

This module is used to register context processor`
"""

import re

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from base.models import Company, TrackLateComeEarlyOut
from base.urls import urlpatterns
from employee.models import (
    Employee,
    EmployeeGeneralSetting,
    EmployeeWorkInformation,
    ProfileEditFeature,
)
from skylinx.decorators import hx_request_required, login_required, permission_required
from skylinx.http.response import SkylinxRedirect
from skylinx.methods import get_skylinx_model_class

CACHE_TIMEOUT = getattr(settings, "CACHE_TIMEOUT", 3600)


class AllCompany:
    """
    Dummy class
    """

    class Urls:
        url = "https://ui-avatars.com/api/?name=All+Company&background=random"

    company = "All Company"
    icon = Urls()
    text = "All companies"
    id = None


def get_last_section(path):
    # Remove any trailing slash and split the path
    segments = path.strip("/").split("/")

    # Get the last section (the ID)
    last_section = segments[-1] if segments else None
    return last_section


def get_companies(request):
    """
    Build the company switcher options.

    Only superusers (or users holding ``base.view_company``) may see every
    company and the "All Company" option. Every other user is limited to their
    own company so they cannot view or switch into other companies' data.
    """
    user = getattr(request, "user", None)
    # Only the superuser (admin) may view every company and switch to
    # "All Company"; everyone else is limited to their own company.
    is_privileged = bool(user and user.is_authenticated and user.is_superuser)

    if is_privileged:
        company_qs = Company.objects.all()
    else:
        # Restrict ordinary users to their own company only.
        company_qs = Company.objects.none()
        try:
            own_company = request.user.employee_get.employee_work_info.company_id
            if own_company:
                company_qs = Company.objects.filter(id=own_company.id)
        except Exception:
            company_qs = Company.objects.none()

    companies = list(
        [company.id, company.company if (company.company and "skylinx" not in company.company.lower()) else "EMPLINX", company.icon.url, False]
        for company in company_qs
    )

    if is_privileged:
        companies = [
            [
                "all",
                "All Company",
                "https://ui-avatars.com/api/?name=All+Company&background=random",
                False,
            ],
        ] + companies

    selected_company = None
    if request and hasattr(request, 'session'):
        selected_company = request.session.get("selected_company")

    # Non-privileged users must never be scoped to "all" or another company.
    if not is_privileged:
        allowed_ids = {str(c[0]) for c in companies}
        if selected_company and str(selected_company) not in allowed_ids:
            selected_company = str(companies[0][0]) if companies else None
            if request and hasattr(request, 'session'):
                request.session["selected_company"] = selected_company

    company_selected = False
    if is_privileged and selected_company == "all":
        if companies:
            companies[0][3] = True
        company_selected = True
    else:
        for company in companies:
            if str(company[0]) == str(selected_company):
                company[3] = True
                company_selected = True
    return {"all_companies": companies, "company_selected": company_selected}


@login_required
@hx_request_required
@permission_required("base.change_company")
def update_selected_company(request):
    """
    This method is used to update the selected company on the session
    """
    company_id = request.GET.get("company_id")
    user = request.user.employee_get
    user_company = getattr(
        getattr(user, "employee_work_info", None), "company_id", None
    )
    # Only the superuser may switch to "All Company" or into a company other
    # than their own. Everyone else is pinned to their own company.
    if not request.user.is_superuser:
        own_id = getattr(user_company, "id", None)
        if company_id == "all" or (own_id is not None and str(company_id) != str(own_id)):
            return HttpResponse(status=403)
    request.session["selected_company"] = company_id
    company = (
        AllCompany()
        if company_id == "all"
        else (
            Company.objects.filter(id=company_id).first()
            if Company.objects.filter(id=company_id).first()
            else AllCompany()
        )
    )
    previous_path = request.GET.get("next", "/")
    # Define the regex pattern for the path
    pattern = r"^/employee/employee-view/\d+/$"
    # Check if the previous path matches the pattern
    if company_id != "all":
        if re.match(pattern, previous_path):
            employee_id = get_last_section(previous_path)
            employee = Employee.objects.filter(id=employee_id).first()
            emp_company = getattr(
                getattr(employee, "employee_work_info", None), "company_id", None
            )
            if emp_company != company:
                text = "Other Company"
                if company_id == user_company:
                    text = "My Company"
                company = {
                    "company": company.company,
                    "icon": company.icon.url,
                    "text": text,
                    "id": company.id,
                }
                messages.error(
                    request, _("Employee is not working in the selected company.")
                )
                request.session["selected_company_instance"] = company
                return HttpResponse(
                    f"""
                    <script>window.location.href = `{reverse("employee-view")}`</script>
                """
                )

    if company_id == "all":
        text = "All companies"
    elif company_id == user_company:
        text = "My Company"
    else:
        text = "Other Company"

    company = {
        "company": company.company if (company.company and "skylinx" not in company.company.lower()) else "EMPLINX",
        "icon": company.icon.url,
        "text": text,
        "id": company.id,
    }
    request.session["selected_company_instance"] = company
    return SkylinxRedirect(request)


urlpatterns.append(
    path(
        "update-selected-company/",
        update_selected_company,
        name="update-selected-company",
    )
)


def white_labelling_company(request):
    white_labelling = getattr(settings, "WHITE_LABELLING", False)
    if white_labelling:
        hq = Company.objects.filter(hq=True).last()
        try:
            if request and hasattr(request, 'user') and hasattr(request.user, 'employee_get'):
                company = (
                    request.user.employee_get.get_company()
                    if request.user.employee_get.get_company()
                    else hq
                )
            else:
                company = hq
        except:
            company = hq

        company_name = company.company if company else "EMPLINX"
        if not company_name or "skylinx" in company_name.lower():
            company_name = "EMPLINX"

        return {
            "white_label_company_name": company_name,
            "white_label_company": company,
        }
    else:
        return {
            "white_label_company_name": "EMPLINX",
            "white_label_company": None,
        }


def resignation_request_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    if request is None:
        selected_company = None
    else:
        selected_company = request.session.get("selected_company")
    cache_key = f"resignation_request_enabled_{selected_company}"
    enabled_resignation_request = cache.get(cache_key)
    
    if enabled_resignation_request is None:
        enabled_resignation_request = False
        first = None
        if apps.is_installed("offboarding"):
            OffboardingGeneralSetting = get_skylinx_model_class(
                app_label="offboarding", model="offboardinggeneralsetting"
            )
            if selected_company and selected_company != "all":
                first = OffboardingGeneralSetting.objects.filter(
                    company_id=selected_company
                ).first()
            else:
                first = OffboardingGeneralSetting.objects.first()
        if first:
            enabled_resignation_request = first.resignation_request
        cache.set(cache_key, enabled_resignation_request, CACHE_TIMEOUT)
    
    return {"enabled_resignation_request": enabled_resignation_request}


def timerunner_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    cache_key = "timerunner_enabled"
    enabled_timerunner = cache.get(cache_key)
    
    if enabled_timerunner is None:
        first = None
        enabled_timerunner = True
        if apps.is_installed("attendance"):
            AttendanceGeneralSetting = get_skylinx_model_class(
                app_label="attendance", model="attendancegeneralsetting"
            )
            first = AttendanceGeneralSetting.objects.first()
        if first:
            enabled_timerunner = first.time_runner
        cache.set(cache_key, enabled_timerunner, CACHE_TIMEOUT)
    
    return {"enabled_timerunner": enabled_timerunner}


def intial_notice_period(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    cache_key = "initial_notice_period"
    initial = cache.get(cache_key)
    
    if initial is None:
        initial = 30
        first = None
        if apps.is_installed("payroll"):
            PayrollGeneralSetting = get_skylinx_model_class(
                app_label="payroll", model="payrollgeneralsetting"
            )
            first = PayrollGeneralSetting.objects.first()
        if first:
            initial = first.notice_period
        cache.set(cache_key, initial, CACHE_TIMEOUT)
    
    return {"get_initial_notice_period": initial}


def check_candidate_self_tracking(request):
    """
    This method is used to get the candidate self tracking is enabled or not
    """

    if request is None:
        selected_company = None
    else:
        selected_company = request.session.get("selected_company")
    cache_key = f"candidate_self_tracking_{selected_company}"
    candidate_self_tracking = cache.get(cache_key)
    
    if candidate_self_tracking is None:
        candidate_self_tracking = False
        if apps.is_installed("recruitment"):
            RecruitmentGeneralSetting = get_skylinx_model_class(
                app_label="recruitment", model="recruitmentgeneralsetting"
            )
            if selected_company and selected_company != "all":
                first = RecruitmentGeneralSetting.objects.filter(
                    company_id_id=selected_company
                ).first()
            else:
                first = RecruitmentGeneralSetting.objects.filter(
                    company_id__isnull=True
                ).first()
        else:
            first = None
        if first:
            candidate_self_tracking = first.candidate_self_tracking
        cache.set(cache_key, candidate_self_tracking, CACHE_TIMEOUT)
    
    return {"check_candidate_self_tracking": candidate_self_tracking}


def check_candidate_self_tracking_rating(request):
    """
    This method is used to check enabled/disabled of rating option
    """
    if request is None:
        selected_company = None
    else:
        selected_company = request.session.get("selected_company")
    cache_key = f"candidate_self_tracking_rating_{selected_company}"
    rating_option = cache.get(cache_key)
    
    if rating_option is None:
        rating_option = False
        if apps.is_installed("recruitment"):
            RecruitmentGeneralSetting = get_skylinx_model_class(
                app_label="recruitment", model="recruitmentgeneralsetting"
            )
            if selected_company and selected_company != "all":
                first = RecruitmentGeneralSetting.objects.filter(
                    company_id_id=selected_company
                ).first()
            else:
                first = RecruitmentGeneralSetting.objects.filter(
                    company_id__isnull=True
                ).first()
        else:
            first = None
        if first:
            rating_option = first.show_overall_rating
        cache.set(cache_key, rating_option, CACHE_TIMEOUT)
    
    return {"check_candidate_self_tracking_rating": rating_option}


def get_initial_prefix(request):
    """
    This method is used to get the initial prefix
    """
    cache_key = "initial_prefix"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        settings = EmployeeGeneralSetting.objects.first()
        instance_id = None
        prefix = "PEP"
        if settings:
            instance_id = settings.id
            prefix = settings.badge_id_prefix
        cached_data = {"prefix": prefix, "instance_id": instance_id}
        cache.set(cache_key, cached_data, CACHE_TIMEOUT)
    
    return {"get_initial_prefix": cached_data["prefix"], "prefix_instance_id": cached_data["instance_id"]}


def biometric_app_exists(request):
    from django.conf import settings

    biometric_app_exists = "biometric" in settings.INSTALLED_APPS
    return {"biometric_app_exists": biometric_app_exists}


def enable_late_come_early_out_tracking(request):
    if request is None:
        selected_company = "all"
    else:
        selected_company = request.session.get("selected_company", "all")
    cache_key = f"late_come_early_out_tracking_{selected_company}"
    enable = cache.get(cache_key)
    
    if enable is None:
        if request is None:
            tracking = TrackLateComeEarlyOut.objects.first()
            enable = tracking.is_enable if tracking else True
        else:
            if selected_company == "all":
                company = None
            else:
                company = Company.objects.filter(id=selected_company).first()

            tracking = TrackLateComeEarlyOut.objects.filter(company_id=company).first()
            enable = tracking.is_enable if tracking else True
        cache.set(cache_key, enable, CACHE_TIMEOUT)
    
    return {"tracking": enable, "late_come_early_out_tracking": enable}


def enable_profile_edit(request):
    from accessibility.accessibility import ACCESSBILITY_FEATURE

    cache_key = "profile_edit_enabled"
    enable = cache.get(cache_key)
    
    if enable is None:
        profile_edit = ProfileEditFeature.objects.filter().first()
        enable = False if profile_edit and profile_edit.is_enabled else True
        cache.set(cache_key, enable, CACHE_TIMEOUT)
    
    if enable:
        if not any(item[0] == "profile_edit" for item in ACCESSBILITY_FEATURE):
            ACCESSBILITY_FEATURE.append(("profile_edit", _("Profile Edit Access")))

    return {"profile_edit_enabled": enable}
