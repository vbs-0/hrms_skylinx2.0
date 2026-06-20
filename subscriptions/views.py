"""
Platform-owner console (superuser only) + the client-facing blocked pages.

Console (/manage/):
  * list every company with its subscription, plan, seats, status
  * onboard a new client (company + admin login + subscription)
  * change a company's plan / status (suspend / reactivate / extend)
  * "log in as" a client admin for support (impersonation)

Client pages:
  * /subscription/inactive/  shown when a company's subscription isn't live
  * /subscription/locked/    shown when a module isn't in the company's plan
"""

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from base.models import Company
from employee.models import Employee, EmployeeWorkInformation

from .features import PAID_FEATURES
from .models import Plan, Subscription

User = get_user_model()

superuser_required = user_passes_test(lambda u: u.is_superuser)

# apps a freshly onboarded company admin can manage
COMPANY_ADMIN_APPS = [
    "employee",
    "attendance",
    "leave",
    "payroll",
    "recruitment",
    "pms",
    "asset",
    "base",
]


def _plan_or_none(plan_id):
    """Safely resolve a plan id from form input ('' / non-numeric -> None)."""
    if not plan_id or not str(plan_id).isdigit():
        return None
    return Plan.objects.filter(id=plan_id).first()


def _company_admin_group():
    """A reusable group granting broad (non-superuser) management permissions."""
    group, created = Group.objects.get_or_create(name="Company Admin")
    if created:
        perms = Permission.objects.filter(
            content_type__app_label__in=COMPANY_ADMIN_APPS
        )
        group.permissions.set(perms)
    return group


@login_required
@superuser_required
def console(request):
    companies = Company.objects.all().order_by("company")
    rows = []
    for c in companies:
        sub = getattr(c, "subscription", None)
        # a non-superuser user in this company we can impersonate for support
        admin_user = (
            User.objects.filter(
                is_superuser=False,
                employee_get__employee_work_info__company_id=c,
            )
            .order_by("id")
            .first()
        )
        rows.append(
            {
                "company": c,
                "sub": sub,
                "seats_used": sub.seats_used() if sub else 0,
                "seat_limit": sub.seat_limit if sub else None,
                "admin_user": admin_user,
            }
        )
    context = {
        "rows": rows,
        "plans": Plan.objects.filter(is_active=True),
        "statuses": ["trial", "active", "past_due", "suspended", "cancelled"],
        "total_companies": companies.count(),
        "live_count": sum(1 for r in rows if r["sub"] and r["sub"].is_live),
    }
    return render(request, "subscriptions/console.html", context)


@login_required
@superuser_required
def onboard(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        admin_username = request.POST.get("admin_username", "").strip()
        admin_email = request.POST.get("admin_email", "").strip()
        admin_password = request.POST.get("admin_password", "").strip()
        plan_id = request.POST.get("plan")
        trial_days = int(request.POST.get("trial_days") or 14)

        if not (company_name and admin_username and admin_password):
            messages.error(request, "Company name, admin username and password are required.")
            return redirect("subscriptions-onboard")
        if User.objects.filter(username=admin_username).exists():
            messages.error(request, "That admin username already exists.")
            return redirect("subscriptions-onboard")

        # Employee.email is unique & required — synthesize one if not given.
        if not admin_email:
            admin_email = f"{admin_username}@{company_name.lower().replace(' ', '')}.local"

        try:
            with transaction.atomic():
                company = Company.objects.create(company=company_name)
                user = User.objects.create_user(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                )
                # NOTE: do NOT set is_staff — Django admin (/admin/) is not
                # tenant-scoped, so staff access would leak other companies'
                # data. HRMS permissions come from the Company Admin group.
                user.groups.add(_company_admin_group())
                user.save()
                emp = Employee.objects.create(
                    employee_first_name=company_name,
                    employee_user_id=user,
                    email=admin_email,
                )
                # Creating the Employee auto-makes its work-info row (signal),
                # so update that one with the company rather than creating a 2nd.
                wi, _ = EmployeeWorkInformation.objects.get_or_create(
                    employee_id=emp
                )
                wi.company_id = company
                wi.save()
                plan = _plan_or_none(plan_id)
                Subscription.objects.create(
                    company=company,
                    plan=plan,
                    status="trial",
                    trial_ends_on=timezone.now().date() + timedelta(days=trial_days),
                )
            messages.success(
                request, f"Onboarded {company_name}. Admin login: {admin_username}"
            )
        except Exception as e:
            messages.error(request, f"Onboarding failed: {e}")
        return redirect("subscriptions-console")

    return render(
        request,
        "subscriptions/onboard.html",
        {"plans": Plan.objects.filter(is_active=True)},
    )


@login_required
@superuser_required
def subscription_update(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    sub, _ = Subscription.objects.get_or_create(company=company)
    action = request.POST.get("action")

    if action == "set_plan":
        sub.plan = _plan_or_none(request.POST.get("plan"))
    elif action == "set_status":
        sub.status = request.POST.get("status", sub.status)
    elif action == "extend":
        days = int(request.POST.get("days") or 30)
        base = sub.expires_on or timezone.now().date()
        sub.expires_on = base + timedelta(days=days)
        if sub.status in ("suspended", "cancelled", "past_due"):
            sub.status = "active"
    sub.save()
    messages.success(request, f"Updated subscription for {company}.")
    return redirect("subscriptions-console")


@login_required
@superuser_required
def impersonate(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target.is_superuser:
        messages.error(request, "Refusing to impersonate another superuser.")
        return redirect("subscriptions-console")
    original_id = request.user.id
    # login() flushes the session when switching users, so set the marker AFTER.
    login(request, target)
    request.session["impersonator_id"] = original_id
    messages.info(request, f"You are now viewing as {target.username}.")
    return redirect("/")


@login_required
def stop_impersonate(request):
    impersonator_id = request.session.pop("impersonator_id", None)
    if impersonator_id:
        original = User.objects.filter(id=impersonator_id).first()
        if original:
            login(request, original)
            messages.info(request, "Returned to your platform-owner account.")
    return redirect("subscriptions-console")


# ----- client-facing blocked pages -----

@login_required
def subscription_inactive(request):
    return render(
        request,
        "subscriptions/inactive.html",
        {"subscription": getattr(getattr(request.user, "employee_get", None), "id", None)},
    )


@login_required
def feature_locked(request):
    key = request.GET.get("f", "")
    meta = PAID_FEATURES.get(key, {})
    return render(
        request,
        "subscriptions/locked.html",
        {"feature_label": meta.get("label", "This module")},
    )
