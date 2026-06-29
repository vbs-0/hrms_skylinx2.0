"""
policies.py

This module is used to write operation related to policies
"""

import datetime
import json
from datetime import timedelta
from urllib.parse import parse_qs

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.methods import (
    closest_numbers,
    eval_validate,
    filtersubordinates,
    get_key_instances,
    paginator_qry,
)
from base.views import paginator_qry
from employee.filters import DisciplinaryActionFilter, PolicyFilter
from employee.forms import DisciplinaryActionForm, PolicyForm
from employee.models import (
    Actiontype,
    DisciplinaryAction,
    Employee,
    Policy,
    PolicyMultipleFile,
)
from skylinx.decorators import hx_request_required, login_required, permission_required
from skylinx.http.response import SkylinxRedirect
from skylinx_auth.models import SkylinxUser
from notifications.signals import notify


@login_required
def view_policies(request):
    """
    Method is used render template to view all the policy records
    """
    policies = Policy.objects.all()
    if not request.user.has_perm("employee.view_policy"):
        policies = policies.filter(is_visible_to_all=True)
    return render(
        request,
        "policies/view_policies.html",
        {"policies": paginator_qry(policies, request.GET.get("page"))},
    )


@login_required
@hx_request_required
@permission_required("employee.add_policy")
def create_policy(request):
    """
    Method is used to create/update new policy
    """
    instance_id = request.GET.get("instance_id")
    instance = None
    if isinstance(eval_validate(str(instance_id)), int):
        instance = Policy.objects.filter(id=instance_id).first()
    form = PolicyForm(instance=instance)
    if request.method == "POST":
        form = PolicyForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            is_new = instance is None
            policy = form.save()
            if is_new:
                from base.models import Company
                selected_company = request.session.get("selected_company")
                company = None
                if selected_company and selected_company != "all":
                    company = Company.objects.filter(id=selected_company).first()
                if not company and hasattr(request.user, "employee_get") and request.user.employee_get:
                    work_info = getattr(request.user.employee_get, "employee_work_info", None)
                    if work_info:
                        company = work_info.company_id
                if not company:
                    company = Company.objects.first()
                if company:
                    policy.company_id.add(company)
            messages.success(request, "Policy saved")
            form = PolicyForm()
            # return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "policies/form.html", {"form": form})


@login_required
@hx_request_required
def search_policies(request):
    """
    This method is used to search in policies
    """
    policies = PolicyFilter(request.GET).qs
    if not request.user.has_perm("employee.view_policy"):
        policies = policies.filter(is_visible_to_all=True)
    return render(
        request,
        "policies/records.html",
        {
            "policies": paginator_qry(policies, request.GET.get("page")),
            "pd": request.GET.urlencode(),
        },
    )


@login_required
@hx_request_required
def view_policy(request):
    """
    This method is used to view the policy
    """
    instance_id = request.GET["instance_id"]
    policy = Policy.objects.filter(id=instance_id).first()
    return render(
        request,
        "policies/view_policy.html",
        {
            "policy": policy,
        },
    )


@login_required
@permission_required("employee.delete_policy")
def delete_policies(request):
    """
    This method is to delete policy
    """
    try:
        ids = request.GET.getlist("ids")
        count, dict = Policy.objects.filter(id__in=ids).delete()
        if count == 0:
            messages.error(request, _("Policies Not Found"))
        else:
            messages.success(request, "Policies deleted")
    except ValueError:
        messages.error(request, _("Policies Not Found"))
    if request.META.get("HTTP_HX_REQUEST"):
        policies_qs = Policy.objects.all()
        if not request.user.has_perm("employee.view_policy"):
            policies_qs = policies_qs.filter(is_visible_to_all=True)
        return render(
            request,
            "policies/records.html",
            {
                "policies": paginator_qry(policies_qs, request.GET.get("page")),
                "pd": request.GET.urlencode(),
            },
        )
    return redirect(view_policies)


@login_required
@permission_required("employee.add_policymultiplefile")
def add_attachment(request):
    """
    This method is used to add attachment to policy
    """
    policy = Policy.find(request.GET.get("policy_id"))
    if not policy:
        return SkylinxRedirect(
            request, message=_("No Policy found matching the query.")
        )

    files = request.FILES.getlist("files")
    attachments = []
    for file in files:
        attachment = PolicyMultipleFile()
        attachment.attachment = file
        attachment.save()
        attachments.append(attachment)
    policy.attachments.add(*attachments)
    messages.success(request, "Attachments added")
    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
@permission_required("employee.delete_policymultiplefile")
def remove_attachment(request):
    """
    This method is used to remove the attachments
    """
    policy = Policy.find(request.GET.get("policy_id"))
    if not policy:
        return SkylinxRedirect(
            request, message=_("No Policy found matching the query.")
        )

    ids = request.GET.getlist("ids")
    PolicyMultipleFile.objects.filter(id__in=ids).delete()
    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
def get_attachments(request):
    """
    This method is used to view all the attachments inside the policy
    """
    policy = Policy.find(request.GET.get("policy_id"))
    if not policy:
        return SkylinxRedirect(
            request, message=_("No Policy found matching the query.")
        )

    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
def disciplinary_actions(request):
    """
    This method is used to view all Disciplinaryaction
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    if request.user.has_perm("employee.view_disciplinaryaction"):
        dis_actions = DisciplinaryAction.objects.all()
    else:
        dis_actions = filtersubordinates(
            request, DisciplinaryAction.objects.all(), "base.add_disciplinaryaction"
        ).distinct()
        dis_actions = (
            dis_actions
            | DisciplinaryAction.objects.filter(employee_id=employee).distinct()
        )

    form = DisciplinaryActionFilter(request.GET, queryset=dis_actions)
    page_number = request.GET.get("page")
    page_obj = paginator_qry(form.qs, page_number)
    previous_data = request.GET.urlencode()

    return render(
        request,
        "disciplinary_actions/disciplinary_nav.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "f": form,
        },
    )


def get_action_type(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id["action"])
    return action.action_type


def get_action_type_delete(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id)
    return action.action_type


def get_action_type(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id["action"])
    return action.action_type


def get_action_type_delete(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id)
    return action.action_type


@login_required
@hx_request_required
@permission_required("employee.add_disciplinaryaction")
def create_actions(request):
    """
    Method is used to create Disciplinaryaction
    """
    form = DisciplinaryActionForm()
    employees = []
    dynamic = (
        request.GET.get("dynamic") if request.GET.get("dynamic") != "None" else None
    )
    if request.GET:
        form = DisciplinaryActionForm(request.GET)

    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES)
        if form.is_valid():
            employee_ids = form.cleaned_data["employee_id"]

            for employee in employee_ids:
                user = employee.employee_user_id
                employees.append(user)

            form.save()
            messages.success(request, _("Disciplinary action taken."))
            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )
        dis = DisciplinaryAction.objects.all()
        if len(dis) == 1:
            return SkylinxRedirect(request)

    return render(
        request, "disciplinary_actions/form.html", {"form": form, "dynamic": dynamic}
    )


@login_required
@hx_request_required
@permission_required("employee.change_disciplinaryaction")
def update_actions(request, action_id):
    """
    Method is used to update Disciplinaryaction
    """

    action = DisciplinaryAction.objects.get(id=action_id)
    form = DisciplinaryActionForm(instance=action)
    employees = []
    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES, instance=action)

        if form.is_valid():
            employee_ids = form.cleaned_data["employee_id"]

            for employee in employee_ids:
                name = employee.employee_user_id
                employees.append(name)

            form.save()
            messages.success(request, _("Disciplinary action updated."))

            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )
    return render(request, "disciplinary_actions/update_form.html", {"form": form})


@login_required
@hx_request_required
@permission_required("employee.change_disciplinaryaction")
def remove_employee_disciplinary_action(request, action_id, emp_id):
    dis_action = DisciplinaryAction.objects.get(id=action_id)
    employee = Employee.objects.get(id=emp_id)

    action_type = get_action_type_delete(dis_action.action)

    if action_type == "dismissal" or action_type == "suspension":
        emp = get_object_or_404(Employee, id=emp_id)
        user = get_object_or_404(SkylinxUser, id=emp.employee_user_id.id)
        if user.is_active:
            pass
        else:
            messages.warning(
                request, _("Employees login credentials will be unblocked.")
            )
            user.is_active = True
            user.save()

    dis_action.employee_id.remove(employee)

    employees = len(dis_action.employee_id.all())

    if employees == 0:
        dis_action.delete()

    messages.success(
        request, _("Employee removed from disciplinary action successfully.")
    )
    return redirect(f"/employee/disciplinary-actions-list?click_id={dis_action.id}")


@login_required
@hx_request_required
@permission_required("employee.delete_disciplinaryaction")
def delete_actions(request, action_id):
    """
    This method is used to delete Disciplinary action
    """
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()

    dis = DisciplinaryAction.objects.get(id=action_id)

    action_type = get_action_type_delete(dis.action)

    for dis_emp in dis.employee_id.all():

        if action_type == "dismissal" or action_type == "suspension":
            employee = get_object_or_404(Employee, id=dis_emp.id)
            user = get_object_or_404(SkylinxUser, id=employee.employee_user_id.id)
            if user.is_active:
                pass
            else:
                messages.warning(
                    request, _("Employees login credentials will be unblocked.")
                )
                user.is_active = True
                user.save()

    dis.delete()
    messages.success(request, _("Disciplinary action deleted."))
    dis_actions = DisciplinaryAction.objects.all()

    hx_target = request.META.get("HTTP_HX_TARGET")
    if hx_target and hx_target == "genericModalBody":
        instances_ids = request.GET.get("instances_ids")
        instances_list = json.loads(instances_ids)
        if action_id in instances_list:
            instances_list.remove(action_id)
            previous_instance, next_instance = closest_numbers(
                json.loads(instances_ids), action_id
            )
        return redirect(
            f"/employee/disciplinary-actions-detail-view/{next_instance}/?{previous_data}&instance_ids={instances_list}&deleted=true"
        )

    if dis_actions.exists():
        return redirect(reverse("disciplinary-actions-list"))
    return SkylinxRedirect(request)


@login_required
def action_type_details(request):
    """
    This method is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.find(request.POST.get("action_type"))
    action_type = action.action_type if action else ""
    return JsonResponse({"action_type": action_type})


@login_required
def action_type_name(request):
    """
    This method is used to get the action type name by the selection of type in the form.
    """
    action_type = request.POST.get("action_type")
    return JsonResponse({"action_type": action_type})


@login_required
@hx_request_required
def disciplinary_filter_view(request):
    """
    This method is used to filter Disciplinary Action.
    """

    previous_data = request.GET.urlencode()
    action_id = request.GET.get("click_id") if request.GET.get("click_id") else None
    dis_filter = DisciplinaryActionFilter(request.GET).qs
    page_number = request.GET.get("page")
    page_obj = paginator_qry(dis_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(DisciplinaryAction, data_dict)
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "dashboard": request.GET.get("dashboard"),
            "action_id": action_id,
        },
    )


@login_required
@hx_request_required
def search_disciplinary(request):
    """
    This method is used to search in Disciplinary Actions
    """
    disciplinary = DisciplinaryActionFilter(request.GET).qs
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": paginator_qry(disciplinary, request.GET.get("page")),
            "pd": request.GET.urlencode(),
        },
    )

@login_required
def accept_policy(request):
    if request.method == "POST":
        policy_id = request.POST.get("policy_id")
        policy = get_object_or_404(Policy, id=policy_id)
        employee = getattr(request.user, "employee_get", None)
        if employee:
            policy.accepted_employees.add(employee)
            return render(
                request,
                "policies/accept_section.html",
                {"policy": policy, "request": request}
            )
    return HttpResponse("Invalid request", status=400)


def pending_mandatory_policies(employee):
    """Mandatory policies visible to this employee that they haven't accepted yet.
    Fail-open: returns none on any missing data so a glitch never locks anyone out."""
    from django.db.models import Q

    if not employee:
        return Policy.objects.none()
    qs = Policy.objects.filter(mandatory=True)
    company = getattr(
        getattr(employee, "employee_work_info", None), "company_id", None
    )
    if company:
        qs = qs.filter(company_id=company)
    qs = qs.filter(
        Q(is_visible_to_all=True) | Q(specific_employees=employee)
    ).distinct()
    return qs.exclude(accepted_employees=employee)


@login_required
def policy_gate(request):
    """Blocking page: employee must accept all pending mandatory policies to proceed."""
    employee = getattr(request.user, "employee_get", None)
    pending = pending_mandatory_policies(employee)
    if request.method == "POST":
        if employee:
            for policy in pending:
                policy.accepted_employees.add(employee)
        return redirect("/")
    if not pending:
        return redirect("/")
    return render(request, "policies/policy_gate.html", {"policies": pending})


@login_required
@permission_required("employee.add_policy")
def policy_acceptance_status(request):
    """HR/CEO view: per mandatory policy, who accepted vs who is still pending.
    Strictly scoped to the viewer's own company so one company never sees
    another company's policies or employees."""
    viewer = getattr(request.user, "employee_get", None)
    company = getattr(
        getattr(viewer, "employee_work_info", None), "company_id", None
    )
    rows = []
    if not company:
        return render(request, "policies/acceptance_status.html", {"rows": rows})

    # Only policies explicitly tied to this company (excludes orphan/shared rows).
    policies = Policy.objects.filter(mandatory=True, company_id=company).distinct()
    company_employees = Employee.objects.filter(
        employee_work_info__company_id=company
    )
    for policy in policies:
        accepted = policy.accepted_employees.filter(
            employee_work_info__company_id=company
        )
        if policy.is_visible_to_all:
            applicable = company_employees
        else:
            applicable = policy.specific_employees.filter(
                employee_work_info__company_id=company
            )
        accepted_ids = list(accepted.values_list("id", flat=True))
        rows.append(
            {
                "policy": policy,
                "accepted": accepted,
                "pending": applicable.exclude(id__in=accepted_ids),
            }
        )
    return render(request, "policies/acceptance_status.html", {"rows": rows})
