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

import json
import re

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

from base.models import Company
from employee.models import Employee, EmployeeWorkInformation

from . import billing
from .features import PAID_FEATURES
from .models import Plan, Subscription
from .utils import company_for_user, subscription_for_company

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
    # always ensure group/permission management is available (safe to re-add)
    group_perms = Permission.objects.filter(
        content_type__app_label="auth",
        codename__in=["add_group", "change_group", "delete_group", "view_group", "view_permission"],
    )
    group.permissions.add(*group_perms)
    return group


def create_tenant(company_name, username, email, password, plan, trial_days=None):
    """
    Create Company + admin user + Employee + trial Subscription atomically.
    Shared by the owner console (onboard) and client self-signup.
    Trial length comes from the chosen plan (owner-editable) unless overridden.
    Returns (company, user); raises on failure.
    """
    if trial_days is None:
        trial_days = plan.trial_days if plan else 14
    # Employee.email is unique & required — synthesize one if not given.
    if not email:
        email = f"{username}@{company_name.lower().replace(' ', '')}.local"
    with transaction.atomic():
        company = Company.objects.create(company=company_name)
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        # NOTE: do NOT set is_staff — Django admin (/admin/) is not tenant-scoped,
        # so staff access would leak other companies' data. HRMS permissions come
        # from the Company Admin group.
        user.groups.add(_company_admin_group())
        user.save()
        emp = Employee.objects.create(
            employee_first_name=company_name, employee_user_id=user, email=email
        )
        # Creating the Employee auto-makes its work-info row (signal), so update
        # that one with the company rather than creating a second.
        wi, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=emp)
        wi.company_id = company
        wi.save()
        Subscription.objects.create(
            company=company,
            plan=plan,
            status="trial",
            trial_ends_on=timezone.now().date() + timedelta(days=trial_days),
        )
    return company, user


def _activate_plan(sub, plan):
    """Apply a paid plan to a subscription: active + expiry by billing cycle."""
    sub.plan = plan
    sub.status = "active"
    days = 365 if plan.billing_cycle == "yearly" else 30
    sub.expires_on = timezone.now().date() + timedelta(days=days)
    sub.notes = ""
    sub.save()


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
    from .features import PAID_FEATURES
    context = {
        "rows": rows,
        "plans": Plan.objects.filter(is_active=True),
        "statuses": ["trial", "active", "past_due", "suspended", "cancelled"],
        "total_companies": companies.count(),
        "live_count": sum(1 for r in rows if r["sub"] and r["sub"].is_live),
        "paid_features": PAID_FEATURES,
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
        td = request.POST.get("trial_days")
        trial_days = int(td) if td and td.isdigit() else None  # None -> plan default

        if not (company_name and admin_username and admin_password):
            messages.error(request, "Company name, admin username and password are required.")
            return redirect("subscriptions-onboard")
        if User.objects.filter(username=admin_username).exists():
            messages.error(request, "That admin username already exists.")
            return redirect("subscriptions-onboard")

        try:
            create_tenant(
                company_name,
                admin_username,
                admin_email,
                admin_password,
                _plan_or_none(plan_id),
                trial_days,
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
    elif action == "toggle_feature":
        key = request.POST.get("feature_key", "")
        overrides = list(sub.feature_overrides or [])
        if key in overrides:
            overrides.remove(key)
        else:
            overrides.append(key)
        sub.feature_overrides = overrides
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


# ----- client self-signup + plan selection / billing -----

def signup(request):
    """Public self-signup: creates a company + admin + 14-day trial, then logs in."""
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        username = request.POST.get("admin_username", "").strip()
        email = request.POST.get("admin_email", "").strip()
        password = request.POST.get("admin_password", "").strip()
        if not (company_name and username and password):
            messages.error(request, "Company name, username and password are required.")
            return redirect("subscription-signup")
        if User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return redirect("subscription-signup")
        trial_plan = Plan.objects.filter(is_active=True).order_by("price").first()
        days = trial_plan.trial_days if trial_plan else 14
        try:
            _, user = create_tenant(company_name, username, email, password, trial_plan)
            login(request, user)
            messages.success(
                request, f"Welcome, {company_name}! Your {days}-day trial has started."
            )
            return redirect("/")
        except Exception as e:
            messages.error(request, f"Sign-up failed: {e}")
            return redirect("subscription-signup")
    trial_plan = Plan.objects.filter(is_active=True).order_by("price").first()
    days = trial_plan.trial_days if trial_plan else 14
    return render(request, "subscriptions/signup.html", {"trial_days": days})


@login_required
def client_plans(request):
    """Client view: current subscription + available plans to switch/upgrade."""
    company = company_for_user(request.user)
    sub = subscription_for_company(company)
    return render(
        request,
        "subscriptions/plans.html",
        {
            "company": company,
            "sub": sub,
            "plans": Plan.objects.filter(is_active=True),
            "all_features": PAID_FEATURES,
            "billing_on": billing.configured(),
        },
    )


@login_required
def choose_plan(request):
    """Client picks a plan. Free → apply now; paid → Razorpay checkout (or note)."""
    company = company_for_user(request.user)
    sub = subscription_for_company(company)
    plan = _plan_or_none(request.POST.get("plan"))
    if not (company and sub and plan):
        messages.error(request, "Pick a valid plan.")
        return redirect("subscription-plans")

    if float(plan.price) <= 0:
        _activate_plan(sub, plan)
        messages.success(request, f"You're now on the {plan.name} plan.")
        return redirect("subscription-plans")

    if not billing.configured():
        sub.notes = f"Requested upgrade to: {plan.name}"
        sub.save()
        messages.info(
            request,
            "Online payment isn't enabled yet — your request was sent; we'll activate it shortly.",
        )
        return redirect("subscription-plans")

    try:
        order = billing.create_order(plan.price, f"plan{plan.id}-co{company.id}")
    except Exception as e:
        messages.error(request, f"Could not start checkout: {e}")
        return redirect("subscription-plans")
    return render(
        request,
        "subscriptions/checkout.html",
        {
            "order": order,
            "plan": plan,
            "company": company,
            "key_id": billing.KEY_ID,
        },
    )


@login_required
def pay_verify(request):
    """Razorpay callback: verify signature, then activate the plan."""
    company = company_for_user(request.user)
    sub = subscription_for_company(company)
    plan = _plan_or_none(request.POST.get("plan"))
    ok = billing.verify_signature(
        request.POST.get("razorpay_order_id"),
        request.POST.get("razorpay_payment_id"),
        request.POST.get("razorpay_signature"),
    )
    if sub and plan and ok:
        _activate_plan(sub, plan)
        messages.success(request, f"Payment received — {plan.name} is now active.")
    else:
        messages.error(request, "Payment could not be verified. You were not charged twice; contact support if money was deducted.")
    return redirect("subscription-plans")


def _activate_from_receipt(receipt):
    """receipt is 'plan<P>-co<C>' (set in choose_plan). Activate that plan.

    Idempotent: safe to call again if the webhook is redelivered.
    Returns True if a subscription was activated.
    """
    m = re.match(r"plan(\d+)-co(\d+)", receipt or "")
    if not m:
        return False
    plan = Plan.objects.filter(id=m.group(1)).first()
    sub = Subscription.objects.filter(company_id=m.group(2)).first()
    if not (plan and sub):
        return False
    _activate_plan(sub, plan)
    return True


def _is_company_admin(user):
    return user.is_superuser or user.groups.filter(name="Company Admin").exists()


@login_required
def company_admins(request):
    """Client settings: grant/revoke admin within your own company (gap #30).

    Prevents the 'lone admin leaves → tenant bricked' problem: any admin can
    promote a colleague, so there's always a recoverable second owner.
    """
    company = company_for_user(request.user)
    if not (company and _is_company_admin(request.user)):
        messages.error(request, "Only a company admin can manage admins.")
        return redirect("/")

    admin_group = _company_admin_group()
    people = (
        Employee.objects.filter(employee_work_info__company_id=company)
        .select_related("employee_user_id")
        .order_by("employee_first_name")
    )

    if request.method == "POST":
        action = request.POST.get("action")
        emp = people.filter(id=request.POST.get("employee_id")).first()
        target = getattr(emp, "employee_user_id", None)
        if not target:
            messages.error(request, "Employee not found in your company.")
        elif action == "promote":
            target.groups.add(admin_group)
            messages.success(request, f"{emp} is now a company admin.")
        elif action == "revoke":
            # don't allow removing the last admin (re-bricking the tenant)
            admin_ids = {
                e.employee_user_id_id
                for e in people
                if e.employee_user_id_id
                and e.employee_user_id.groups.filter(name="Company Admin").exists()
            }
            if admin_ids == {target.id}:
                messages.error(request, "Can't remove the only admin — promote someone else first.")
            else:
                target.groups.remove(admin_group)
                messages.success(request, f"{emp} is no longer a company admin.")
        return redirect("subscription-admins")

    rows = [
        {
            "emp": e,
            "is_admin": bool(
                e.employee_user_id
                and e.employee_user_id.groups.filter(name="Company Admin").exists()
            ),
        }
        for e in people
    ]
    return render(request, "subscriptions/admins.html", {"rows": rows, "company": company})


@csrf_exempt
def razorpay_webhook(request):
    """Server-to-server payment confirmation (gap #5).

    Activates the plan even if the buyer closed the browser before the redirect.
    Configure in Razorpay dashboard → Webhooks → event `order.paid`, with the
    same secret as RAZORPAY_WEBHOOK_SECRET.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    if not billing.verify_webhook(request.body, request.headers.get("X-Razorpay-Signature", "")):
        return HttpResponse("bad signature", status=400)
    try:
        payload = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("bad json")
    # order.paid carries the order entity (with our receipt); ignore other events.
    if payload.get("event") == "order.paid":
        receipt = (
            payload.get("payload", {})
            .get("order", {})
            .get("entity", {})
            .get("receipt", "")
        )
        _activate_from_receipt(receipt)
    return HttpResponse("ok")  # always 200 so Razorpay stops retrying
