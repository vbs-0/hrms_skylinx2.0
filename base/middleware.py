"""
middleware.py
"""
from base.rbac import is_platform_owner


from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from base.backends import ConfiguredEmailBackend
from base.context_processors import AllCompany
from base.skylinx_company_manager import SkylinxCompanyManager
from base.models import Company, ShiftRequest, WorkTypeRequest
from employee.models import (
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeWorkInformation,
)
from skylinx.skylinx_middlewares import _thread_locals, set_selected_company
from skylinx.methods import get_skylinx_model_class
from skylinx_documents.models import DocumentRequest

CACHE_KEY = "skylinx_company_models_cache_key"


# class CompanyMiddleware:
#     """
#     Middleware to handle company-specific filtering for models.
#     """

#     def __init__(self, get_response):
#         self.get_response = get_response

#     def _get_company_id(self, request):
#         """
#         Retrieve the company ID from the request or session.
#         """
#         if getattr(request, "user", False) and not request.user.is_anonymous:
#             try:
#                 if com_id := request.session.get("selected_company", None):
#                     return (
#                         Company.objects.filter(id=com_id).first()
#                         if com_id != "all"
#                         else None
#                     )
#                 else:
#                     return getattr(
#                         request.user.employee_get.employee_work_info, "company_id", None
#                     )
#             except AttributeError:
#                 pass
#         return None

#     def _set_company_session(self, request, company_id):
#         """
#         Set the company session data based on the company ID.
#         """
#         try:
#             user = request.user.employee_get
#         except Exception:
#             logout(request)
#             messages.error(
#                 request,
#                 _("An employee related to this user's credentials does not exist."),
#             )
#             return redirect("login")
#         user_company_id = getattr(
#             getattr(user, "employee_work_info", None), "company_id", None
#         )
#         if company_id and request.session.get("selected_company") != "all":
#             if company_id == "all":
#                 text = "All companies"
#             elif company_id == user_company_id:
#                 text = "My Company"
#             else:
#                 text = "Other Company"

#             request.selected_company_instance = company_id
#             request.session["selected_company"] = str(company_id.id)
#             request.session["selected_company_instance"] = {
#                 "company": company_id.company,
#                 "icon": company_id.icon.url,
#                 "text": text,
#                 "id": company_id.id,
#             }
#         else:
#             request.selected_company_instance = (
#                 user_company_id
#                 if not user_company_id
#                 else Company.objects.filter(hq=True).first()
#             )
#             request.session["selected_company"] = "all"
#             all_company = AllCompany()
#             request.session["selected_company_instance"] = {
#                 "company": all_company.company,
#                 "icon": all_company.icon.url,
#                 "text": all_company.text,
#                 "id": all_company.id,
#             }

#     def _add_company_filter(self, model, company_id):
#         """
#         Add company filter to the model if applicable.
#         """
#         is_company_model = model in self._get_company_models()
#         company_field = getattr(model, "company_id", None)
#         is_skylinx_manager = isinstance(model.objects, SkylinxCompanyManager)
#         related_company_field = getattr(model.objects, "related_company_field", None)

#         if is_company_model:
#             if company_field:
#                 model.add_to_class("company_filter", Q(company_id=company_id))
#             elif is_skylinx_manager and related_company_field:
#                 model.add_to_class(
#                     "company_filter", Q(**{related_company_field: company_id})
#                 )
#         else:
#             if company_field:
#                 model.add_to_class(
#                     "company_filter",
#                     Q(company_id=company_id) | Q(company_id__isnull=True),
#                 )
#             elif is_skylinx_manager and related_company_field:
#                 model.add_to_class(
#                     "company_filter",
#                     Q(**{related_company_field: company_id})
#                     | Q(**{f"{related_company_field}__isnull": True}),
#                 )

#     def _get_company_models(self):
#         """
#         Retrieve the list of models that are company-specific.
#         """
#         company_models = cache.get(CACHE_KEY)

#         if company_models is None:
#             company_models = [
#                 Employee,
#                 ShiftRequest,
#                 WorkTypeRequest,
#                 DocumentRequest,
#                 DisciplinaryAction,
#                 EmployeeBankDetails,
#                 EmployeeWorkInformation,
#             ]

#             app_model_mappings = {
#                 "recruitment": ["recruitment", "candidate"],
#                 "leave": [
#                     "leaverequest",
#                     "restrictleave",
#                     "availableleave",
#                     "leaveallocationrequest",
#                     "compensatoryleaverequest",
#                 ],
#                 "asset": ["assetassignment", "assetrequest"],
#                 "attendance": [
#                     "attendance",
#                     "attendanceactivity",
#                     "attendanceovertime",
#                     "workrecords",
#                 ],
#                 "payroll": [
#                     "contract",
#                     "loanaccount",
#                     "payslip",
#                     "reimbursement",
#                 ],
#                 "helpdesk": ["ticket"],
#                 "offboarding": ["offboarding"],
#                 "pms": ["employeeobjective"],
#             }

#             for app_label, models in app_model_mappings.items():
#                 if apps.is_installed(app_label):
#                     company_models.extend(
#                         [get_skylinx_model_class(app_label, model) for model in models]
#                     )

#             cache.set(CACHE_KEY, company_models)

#         return company_models

#     def __call__(self, request):
#         if getattr(request, "user", False) and not request.user.is_anonymous:
#             company_id = self._get_company_id(request)
#             self._set_company_session(request, company_id)

#             app_models = [
#                 model for model in apps.get_models() if model._meta.app_label in settings.APPS
#             ]
#             for model in app_models:
#                 self._add_company_filter(model, company_id)

#         response = self.get_response(request)
#         return response


class CompanyMiddleware:
    """
    Responsible ONLY for:
    • setting request context
    • deciding current company
    • storing company in contextvar
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_user_default_company(self, request):
        """Fallback if session has no company selected"""
        try:
            return request.user.employee_get.employee_work_info.company_id
        except Exception:
            return None

    def _is_platform_owner(self, request):
        return bool(
            request.user.is_authenticated
            and is_platform_owner(request.user)
            and request.user.username == "skylinx"
        )

    def _get_company_obj(self, request, com_id=None):
        """
        Retrieve the company ID from the request or session.
        """
        if getattr(request, "user", False) and not request.user.is_anonymous:
            try:
                if com_id:
                    return (
                        Company.objects.filter(id=com_id).first()
                        if com_id != "all"
                        else None
                    )
                else:
                    return getattr(
                        request.user.employee_get.employee_work_info, "company_id", None
                    )
            except AttributeError:
                pass
        return None

    def _set_company_session(self, request, company_id):
        """
        Set the company session data based on the company ID.
        """
        try:
            user = getattr(request.user, "employee_get", None)
            if not user:
                raise ValueError("No employee")
        except Exception:
            import sys
            if self._is_platform_owner(request) or "test" in sys.argv:
                request.selected_company_instance = "all"
                request.session["selected_company"] = "all"
                return None
            logout(request)
            messages.error(
                request,
                _("An employee related to this user's credentials does not exist."),
            )
            return redirect("login/")
        user_company_id = getattr(
            getattr(user, "employee_work_info", None), "company_id", None
        )
        if company_id:
            if company_id == "all":
                text = "All companies"
            elif company_id == user_company_id:
                text = "My Company"
            else:
                text = "Other Company"

            request.selected_company_instance = company_id
            request.session["selected_company"] = str(company_id.id)
            request.session["selected_company_instance"] = {
                "company": company_id.company,
                "icon": company_id.icon.url,
                "text": text,
                "id": company_id.id,
            }
        elif self._is_platform_owner(request):
            request.selected_company_instance = (
                user_company_id
                if not user_company_id
                else Company.objects.filter(hq=True).first()
            )
            request.session["selected_company"] = "all"
            all_company = AllCompany()
            request.session["selected_company_instance"] = {
                "company": all_company.company,
                "icon": all_company.icon.url,
                "text": all_company.text,
                "id": all_company.id,
            }
        else:
            request.selected_company_instance = None
            request.session["selected_company"] = None
            request.session["selected_company_instance"] = None

    def __call__(self, request):
        # ✅ make request globally accessible (safe)
        _thread_locals.request = request

        if not request.user.is_authenticated:
            set_selected_company(None)
            return self.get_response(request)

        selected_company = request.session.get("selected_company")

        # --- Determine company ---
        # SECURITY: non-superusers are HARD-LOCKED to their own company. They
        # cannot pick "all" or another tenant's id (would leak cross-company
        # data). Only the platform owner account gets the company switcher.
        if not self._is_platform_owner(request):
            default_company = self._get_user_default_company(request)
            if default_company:
                company_id = default_company.id
                request.session["selected_company"] = str(default_company.id)
            else:
                # no company assigned → see nothing rather than everything
                company_id = None
                request.session["selected_company"] = None
        elif selected_company == "all":
            company_id = "all"

        elif selected_company:
            company_exists = Company.objects.filter(id=selected_company).exists()
            company_id = selected_company if company_exists else None

        else:
            # First login or session expired → set user's own company
            default_company = self._get_user_default_company(request)
            if default_company:
                request.session["selected_company"] = str(default_company.id)
                company_id = default_company.id
            else:
                request.session["selected_company"] = "all"
                company_id = "all"

        # ✅ Store in context
        set_selected_company(company_id)
        company_obj = self._get_company_obj(request, company_id)
        self._set_company_session(request, company_obj)

        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """
    Middleware to force password change for new employees.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_paths = [
            "/change-password",
            "/login",
            "/logout",
            "/get-skylinx-installed-apps",
            "/notifications",
            "/inbox/notifications",
            "/jsi18n",
            "/reload-messages",
            "/subscription"
        ]
        # Check if path starts with any of the excluded paths
        excluded = False
        path = request.path.rstrip("/")
        for excluded_path in excluded_paths:
            if path == excluded_path or path.startswith(excluded_path + "/"):
                excluded = True
                break
        
        if excluded:
            return self.get_response(request)

        if hasattr(request, "user") and request.user.is_authenticated:
            # Only redirect if is_new_employee is explicitly True, not defaulting to True
            if getattr(request.user, "is_new_employee", False):
                return redirect("change-password")

        return self.get_response(request)


class PolicyAcceptanceMiddleware:
    """
    Force employees to accept their company's mandatory policies before using the HRMS.
    Fail-open: any error just lets the request through (never lock people out).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from django.urls import reverse

            # The gate + accept endpoints MUST be excluded by their real (app-prefixed)
            # paths, or the gate redirects to itself forever (ERR_TOO_MANY_REDIRECTS).
            gate_path = reverse("policy-gate").rstrip("/")
            accept_path = reverse("accept-policy").rstrip("/")
        except Exception:
            return self.get_response(request)

        excluded_paths = [
            gate_path,
            accept_path,
            "/login",
            "/logout",
            "/change-password",
            "/two-factor",
            "/notifications",
            "/inbox/notifications",
            "/reload-messages",
            "/jsi18n",
            "/get-skylinx-installed-apps",
            "/subscription",
            "/media",
            "/static",
        ]
        path = request.path.rstrip("/")
        for excluded_path in excluded_paths:
            if path == excluded_path or path.startswith(excluded_path + "/"):
                return self.get_response(request)

        try:
            user = getattr(request, "user", None)
            if (
                user
                and user.is_authenticated
                and not user.is_superuser
                and request.method == "GET"
                and not request.headers.get("HX-Request")
            ):
                from employee.policies import pending_mandatory_policies

                employee = getattr(user, "employee_get", None)
                if employee and pending_mandatory_policies(employee).exists():
                    return redirect(gate_path)
        except Exception:
            pass

        return self.get_response(request)


class TwoFactorAuthMiddleware:
    """
    Middleware to enforce two-factor authentication for specific users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_paths = [
            "/change-password",
            "/login",
            "/logout",
            "/two-factor",
            "/send-otp",
            "/get-skylinx-installed-apps",
            "/notifications",
            "/inbox/notifications",
            "/jsi18n",
            "/reload-messages"
        ]
        # Check if path starts with any of the excluded paths
        excluded = False
        path = request.path.rstrip("/")
        for excluded_path in excluded_paths:
            if path == excluded_path or path.startswith(excluded_path + "/"):
                excluded = True
                break
        
        if excluded:
            return self.get_response(request)

        if settings.TWO_FACTORS_AUTHENTICATION:
            try:
                if ConfiguredEmailBackend().configuration is not None:
                    if hasattr(request, "user") and request.user.is_authenticated:
                        if not request.session.get("otp_code_verified", False):
                            return redirect("/two-factor")
                else:
                    return self.get_response(request)
            except Exception as e:
                return self.get_response(request)

        return self.get_response(request)

class HTMXSecurityMiddleware:
    """
    Middleware to globally enforce authentication and tenant checking on all HTMX requests.
    Prevents unauthenticated access to HTMX views that might lack @login_required.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that are allowed to be accessed via HTMX without auth (e.g. login form interactions)
        self.public_paths = [
            "/login/",
            "/logout/",
            "/change-password/",
            "/two-factor/",
            "/send-otp/",
        ]

    def __call__(self, request):
        if request.headers.get("HX-Request") == "true":
            path = request.path.rstrip("/") + "/"
            is_public = any(path.startswith(p) for p in self.public_paths)
            
            if not is_public and not request.user.is_authenticated:
                # Reject unauthenticated HTMX requests
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Authentication required for this component.")

        return self.get_response(request)
