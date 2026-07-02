"""
This page handles the cbv methods of employee individual view
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from base import views as base_views
from base.cbv.work_shift_tab import WorkAndShiftTabView
from base.context_processors import enable_profile_edit
from base.forms import AddToUserGroupForm
from employee import views
from employee.filters import EmployeeFilter
from employee.models import Employee
from skylinx import settings
from skylinx.http.response import SkylinxRedirect
from skylinx_views.cbv_methods import login_required, permission_required
from skylinx_views.generic.cbv.views import SkylinxProfileView

Employee.cbv_employee_profile_edi_url = reverse_lazy("edit-profile")


@method_decorator(login_required, name="dispatch")
class EmployeeProfileView(SkylinxProfileView):
    """
    EmployeeProfileView
    """

    template_name = "cbv/profile/profile_view.html"

    model = Employee
    filter_class = EmployeeFilter
    push_url = "employee-view-individual"
    key_name = "obj_id"

    # ponytail: only profile-intrinsic tabs; module tabs (Leave, Payroll,
    # Attendance, Projects, Key Results, Scheduled Interviews, Penalty Account,
    # Bonus Points, etc.) live in their own menus, so they're dropped here.
    KEEP_TABS = {
        "About",
        # ponytail: Work Type & Shift dropped — it's already in the sub-module menu
        "Groups & Permissions",
        "Note",
        "Documents",
    }

    def get_queryset(self):
        return Employee.objects.entire()

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        # ponytail: hard-filter tabs at the source so every render path (page +
        # any tab-list partial) only ever sees the profile-intrinsic tabs. Drops
        # Penalty Account, Key Results, Scheduled Interviews, Bonus Points, Leave,
        # Payroll, Attendance, Projects, etc. — they live in their own menus.
        self.tabs = [t for t in type(self).tabs if str(t.get("title")) in self.KEEP_TABS]

        obj_id = kwargs.get("pk")
        if not Employee.objects.entire().filter(id=obj_id).exists():
            return SkylinxRedirect(
                request, message=_("No employee found matching the query.")
            )

        employee = request.user.employee_get

        if request.user.has_perm("employee.change_employee"):
            self.actions = [
                {
                    "title": _("Edit"),
                    "src": f"/{settings.STATIC_URL}images/ui/editing.png",
                    "accessibility": "employee.cbv.accessibility.edit_accessibility",
                    "attrs": """
                        href="#"
                        hx-get="{get_update_url}?container=true"
                        hx-target="#listContainer"
                        hx-swap="innerHTML"
                        hx-push-url="{get_update_url}?container=true"
                        onclick="if (!document.getElementById('listContainer')) {{ event.preventDefault(); event.stopPropagation(); window.location.href = this.getAttribute('hx-get'); return false; }}"
                    """,
                },
                {
                    "title": _("Block Account"),
                    "src": f"/{settings.STATIC_URL}images/ui/block-user.png",
                    "accessibility": "employee.cbv.accessibility.block_account_accessibility",
                    "attrs": """id="block-account" """,
                },
                {
                    "title": _("Un-Block Account"),
                    "src": f"/{settings.STATIC_URL}images/ui/unlock.png",
                    "accessibility": "employee.cbv.accessibility.un_block_account_accessibility",
                    "attrs": """id="block-account" """,
                },
                {
                    "title": _("Send password reset link"),
                    "src": f"/{settings.STATIC_URL}images/ui/key.png",
                    "accessibility": "employee.cbv.accessibility.password_reset_accessibility",
                    "attrs": """onclick="$('#reset-button').click();" """,
                },
            ]
        elif employee.pk == kwargs.get("pk") and enable_profile_edit(request).get(
            "profile_edit_enabled"
        ):
            self.actions = [
                {
                    "title": _("Edit Profile"),
                    "src": f"/{settings.STATIC_URL}images/ui/editing.png",
                    "accessibility": "employee.cbv.accessibility.edit_accessibility",
                    "attrs": """onclick="window.location.href='{cbv_employee_profile_edi_url}'" """,
                },
                {
                    "title": _("Send password reset link"),
                    "src": f"/{settings.STATIC_URL}images/ui/key.png",
                    "accessibility": "employee.cbv.accessibility.password_reset_accessibility",
                    "attrs": """onclick="$('#reset-button').click();" """,
                },
            ]

        return super().dispatch(request, *args, **kwargs)


class UserProfileView(EmployeeProfileView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance_ids"] = None
        if "visible_tabs" in context:
            context["visible_tabs"] = [
                t for t in context["visible_tabs"] if str(t["title"]) in self.KEEP_TABS
            ]
        return context


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": _("About"),
            "view": views.about_tab,
        },
        {
            "title": _("Work Type & Shift"),
            # "view": views.shift_tab,
            "view": WorkAndShiftTabView.as_view(),
            "accessibility": "employee.cbv.accessibility.workshift_accessibility",
        },
        {
            "title": _("Groups & Permissions"),
            "view": base_views.employee_permission_assign,
            "accessibility": "employee.cbv.accessibility.permission_accessibility",
        },
        {
            "title": _("Note"),
            "view": views.note_tab,
            "accessibility": "employee.cbv.accessibility.note_accessibility",
        },
        {
            "title": _("Documents"),
            "view": views.document_tab,
            "accessibility": "employee.cbv.accessibility.document_accessibility",
        },

        # ponytail: Mail Log & History tabs removed from profile UI; backend/urls intact
    ]
)


@method_decorator(
    [login_required, permission_required("auth.add_group")], name="dispatch"
)
class GroupAssignView(View):
    """
    View to assign multiple groups to a single employee
    """

    def get(self, request, *args, **kwargs):
        employee_id = request.GET.get("employee")
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return SkylinxRedirect(
                request, message=_("No Employee found matching the query.")
            )
        groups = employee.employee_user_id.groups.all
        form = AddToUserGroupForm(
            initial={
                "group": groups,
                "employee": request.GET.get("employee"),
            }
        )
        return render(
            request,
            "cbv/auth/user_assign_to_group.html",
            {"form": form, "employee_id": request.GET.get("employee")},
        )

    def post(self, request, *args, **kwargs):
        form = AddToUserGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Employee assigned to group"))
            return SkylinxRedirect(request)
        return render(
            request,
            "cbv/auth/user_assign_to_group.html",
            {"form": form, "employee_id": request.POST.get("employee")},
        )
