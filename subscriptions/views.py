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

# apps a freshly onboarded company admin can manage. Must cover every module
# that shows in the sidebar, otherwise that module's permission-gated nav entry
# is hidden for company admins (e.g. Projects needs a project.* perm).
COMPANY_ADMIN_APPS = [
    "employee",
    "attendance",
    "leave",
    "payroll",
    "recruitment",
    "pms",
    "asset",
    "base",
    "project",
    "helpdesk",
    "biometric",
    "skylinx_documents",
]


def _plan_or_none(plan_id):
    """Safely resolve a plan id from form input ('' / non-numeric -> None)."""
    if not plan_id or not str(plan_id).isdigit():
        return None
    return Plan.objects.filter(id=plan_id).first()


def _company_admin_group():
    """A reusable group granting broad (non-superuser) management permissions."""
    group, created = Group.objects.get_or_create(name="Company Admin")
    # Additively ensure all managed-app perms are present (self-heals existing
    # groups when COMPANY_ADMIN_APPS grows, e.g. adding Projects).
    app_perms = Permission.objects.filter(
        content_type__app_label__in=COMPANY_ADMIN_APPS
    )
    group.permissions.add(*app_perms)
    # always ensure group/permission management is available (safe to re-add)
    group_perms = Permission.objects.filter(
        content_type__app_label="auth",
        codename__in=["add_group", "change_group", "delete_group", "view_group", "view_permission"],
    )
    group.permissions.add(*group_perms)
    return group


# Default per-company roles seeded on company creation. Keys are display labels;
# names are stored tenant-scoped (c<id>::Label) so each company owns its own.
DEFAULT_COMPANY_ROLES = {
    # broad HR access across the daily-use apps
    "HR Manager": {"apps": COMPANY_ADMIN_APPS},
    # team lead: see employees + approve attendance/leave
    "Manager": {
        "codenames": [
            "view_employee",
            "view_attendance", "change_attendance", "add_attendance",
            "view_leaverequest", "change_leaverequest", "add_leaverequest",
            "view_leaveallocationrequest",
            "view_worktyperequest", "change_worktyperequest",
            "view_shiftrequest", "change_shiftrequest",
        ]
    },
    # individual contributor: own profile + raise own requests
    "Employee": {
        "codenames": [
            "view_ownprofile", "change_ownprofile",
            "add_leaverequest", "view_leaverequest",
            "view_attendance",
            "add_worktyperequest", "add_shiftrequest",
        ]
    },
}


def seed_company_groups(company):
    """Create the default per-company roles (idempotent). Returns count created."""
    from base.models import CompanyGroup
    from base.rbac import scoped_name

    created_n = 0
    for label, spec in DEFAULT_COMPANY_ROLES.items():
        name = scoped_name(company.id, label)
        group, created = Group.objects.get_or_create(name=name)
        CompanyGroup.objects.get_or_create(group=group, defaults={"company": company})
        if created:
            if spec.get("apps"):
                perms = Permission.objects.filter(
                    content_type__app_label__in=spec["apps"]
                )
            else:
                perms = Permission.objects.filter(codename__in=spec["codenames"])
            group.permissions.set(perms)
            created_n += 1
    return created_n


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
        # seed default roles (HR Manager / Manager / Employee) for this tenant
        seed_company_groups(company)
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
    # welcome the new company admin (best-effort, host-aware link)
    from base.email_utils import send_company_welcome

    send_company_welcome(company, user, username)
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
def console_analytics(request):
    """Owner-side hub: cross-tenant analytics + per-company access (roles/admins).

    Read-only overview; actions (set plan, password, admins, impersonate) live on
    the main console. This is purely 'see and track everything in one place'.
    """
    from django.contrib.auth.models import Group
    from django.db.models import Count

    from base.models import CompanyGroup
    from base.rbac import strip_name
    from employee.models import Employee
    from .features import PAID_FEATURES

    companies = Company.objects.all().order_by("company")
    subs = {s.company_id: s for s in Subscription.objects.select_related("plan").all()}

    # platform-wide totals
    status_counts = {k: 0 for k in ["trial", "active", "past_due", "suspended", "cancelled"]}
    total_seats_used = total_employees = mrr = 0
    module_adoption = {k: 0 for k in PAID_FEATURES}

    rows = []
    for c in companies:
        sub = subs.get(c.id)
        if sub:
            status_counts[sub.status] = status_counts.get(sub.status, 0) + 1
            if sub.status in ("active",) and sub.plan:
                mrr += float(sub.plan.price or 0)
            feats = list(sub.feature_keys())
            for k in sub.feature_overrides or []:
                if k not in feats:
                    feats.append(k)
            for k in feats:
                if k in module_adoption:
                    module_adoption[k] += 1
        else:
            feats = []

        seats_used = sub.seats_used() if sub else 0
        total_seats_used += seats_used
        emp_count = Employee.objects.filter(
            is_active=True, employee_work_info__company_id=c
        ).count()
        total_employees += emp_count

        # this tenant's roles (CompanyGroup) + admin count
        groups = (
            Group.objects.filter(company_link__company=c)
            .annotate(member_count=Count("user", distinct=True))
        )
        roles = [
            {"name": strip_name(g.name), "members": g.member_count,
             "perms": g.permissions.count()}
            for g in groups
        ]
        admin_count = User.objects.filter(
            is_superuser=False,
            employee_get__employee_work_info__company_id=c,
            groups__name="Company Admin",
        ).count()

        rows.append({
            "company": c,
            "client_id": f"SKX-{c.id:05d}",
            "sub": sub,
            "seats_used": seats_used,
            "seat_limit": sub.seat_limit if sub else None,
            "employees": emp_count,
            "roles": roles,
            "role_count": len(roles),
            "admin_count": admin_count,
            "features": feats,
        })

    adoption = [
        {"label": PAID_FEATURES[k]["label"], "count": n}
        for k, n in module_adoption.items()
    ]
    context = {
        "rows": rows,
        "total_companies": companies.count(),
        "status_counts": status_counts,
        "live_count": status_counts["active"] + status_counts["trial"],
        "total_seats_used": total_seats_used,
        "total_employees": total_employees,
        "mrr": mrr,
        "module_adoption": adoption,
    }
    return render(request, "subscriptions/analytics.html", context)


@login_required
@superuser_required
def console(request):
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    companies = Company.objects.all()
    if search:
        companies = companies.filter(company__icontains=search)
    if status_filter:
        companies = companies.filter(subscription__status=status_filter)

    companies = companies.order_by("company")
    rows = []
    for c in companies:
        sub = getattr(c, "subscription", None)
        admins = User.objects.filter(
            is_superuser=False,
            employee_get__employee_work_info__company_id=c,
            groups__name="Company Admin"
        ).order_by("id")
        
        if not admins.exists():
            admins = User.objects.filter(
                is_superuser=False,
                employee_get__employee_work_info__company_id=c,
            ).order_by("id")

        employee_count = EmployeeWorkInformation.objects.filter(company_id=c).count()
        last_login_admin = admins.order_by("-last_login").first() if admins.exists() else None

        rows.append(
            {
                "company": c,
                "sub": sub,
                "seats_used": sub.seats_used() if sub else 0,
                "seat_limit": sub.seat_limit if sub else None,
                "admins": admins,
                "admin_user": admins.first() if admins.exists() else None,
                "employee_count": employee_count,
                "last_login": last_login_admin.last_login if last_login_admin else None,
            }
        )
    from .features import PAID_FEATURES
    context = {
        "rows": rows,
        "plans": Plan.objects.filter(is_active=True),
        "statuses": ["trial", "active", "past_due", "suspended", "cancelled"],
        "total_companies": Company.objects.count(),
        "live_count": Subscription.objects.filter(status__in=["active", "trial"]).count(),
        "paid_features": PAID_FEATURES,
        "search": search,
        "current_status": status_filter,
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
    elif action == "edit_company":
        company_name = request.POST.get("company_name", "").strip()
        seat_override = request.POST.get("seat_override", "").strip()
        if company_name:
            company.company = company_name
            company.save()
        if seat_override and seat_override.isdigit():
            sub.seat_override = int(seat_override)
        else:
            sub.seat_override = None
    elif action == "delete_tenant":
        confirm_text = request.POST.get("confirm_text", "").strip()
        if confirm_text == company.company:
            company.delete()
            messages.success(request, f"Deleted tenant {confirm_text}.")
            return redirect("subscriptions-console")
        else:
            messages.error(request, "Confirmation text did not match. Tenant not deleted.")
            return redirect("subscriptions-console")
    elif action == "update_admin":
        user_id = request.POST.get("user_id")
        admin = User.objects.filter(id=user_id).first()
        if admin:
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            if username:
                admin.username = username
            if email:
                admin.email = email
            admin.save()
            messages.success(request, f"Updated admin {admin.username}.")
    elif action == "resend_email":
        user_id = request.POST.get("user_id")
        admin = User.objects.filter(id=user_id).first()
        if admin:
            from django.core.mail import send_mail
            from base.backends import ConfiguredEmailBackend
            try:
                backend = ConfiguredEmailBackend()
                send_mail(
                    subject="Welcome to Skylinx!",
                    message=f"Your account for {company.company} has been set up.\nUsername: {admin.username}\nLogin at our portal.",
                    from_email=None,
                    recipient_list=[admin.email],
                    connection=backend,
                    fail_silently=False,
                )
                messages.success(request, f"Email sent to {admin.email}.")
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
    elif action == "set_admin_password":
        user_id = request.POST.get("user_id")
        if user_id:
            admin = User.objects.filter(id=user_id).first()
        else:
            admin = (
                User.objects.filter(
                    is_superuser=False,
                    employee_get__employee_work_info__company_id=company,
                )
                .order_by("id")
                .first()
            )
        new_pw = (request.POST.get("password") or "").strip()
        if not admin:
            messages.error(request, f"No admin user found for {company}.")
            return redirect("subscriptions-console")
        if len(new_pw) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect("subscriptions-console")
        admin.set_password(new_pw)
        admin.save()
        messages.success(
            request, f"Admin password for {company} set. Login username: {admin.username}"
        )
        return redirect("subscriptions-console")
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
    # Multiple auth backends are configured, so name one explicitly.
    login(request, target, backend="django.contrib.auth.backends.ModelBackend")
    request.session["impersonator_id"] = original_id
    messages.info(request, f"You are now viewing as {target.username}.")
    return redirect("/")


@login_required
def stop_impersonate(request):
    impersonator_id = request.session.pop("impersonator_id", None)
    if impersonator_id:
        original = User.objects.filter(id=impersonator_id).first()
        if original:
            login(request, original, backend="django.contrib.auth.backends.ModelBackend")
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
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
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
    from django.conf import settings
    from django.contrib import messages
    from django.shortcuts import redirect

    if not (request.user.is_superuser or request.user.has_perm('subscriptions.change_subscription') or request.user.has_perm('base.change_company')):
        messages.error(request, "You do not have permission to view or change subscriptions.")
        return redirect("/")

    company = company_for_user(request.user)
    sub = subscription_for_company(company)
    # stable, human-friendly client id the client can quote to support
    client_id = f"SKX-{company.id:05d}" if company else None
    return render(
        request,
        "subscriptions/plans.html",
        {
            "company": company,
            "sub": sub,
            "plans": Plan.objects.filter(is_active=True),
            "all_features": PAID_FEATURES,
            "billing_on": billing.configured(),
            "client_id": client_id,
            "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
        },
    )


@login_required
def choose_plan(request):
    """Client picks a plan. Free → apply now; paid → Razorpay checkout (or note)."""
    from django.contrib import messages
    from django.shortcuts import redirect

    if not (request.user.is_superuser or request.user.has_perm('subscriptions.change_subscription') or request.user.has_perm('base.change_company')):
        messages.error(request, "You do not have permission to view or change subscriptions.")
        return redirect("/")

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
            # an admin can't strip their own access — another admin must do it
            if target.id == request.user.id:
                messages.error(
                    request,
                    "You can't revoke your own admin access — ask another admin.",
                )
                return redirect("subscription-admins")
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


@login_required
@superuser_required
def plans_list(request):
    plans = Plan.objects.all().order_by("price")
    return render(request, "subscriptions/plan_list.html", {"plans": plans})


@login_required
@superuser_required
def plan_edit(request, plan_id=None):
    from django import forms

    class PlanForm(forms.ModelForm):
        class Meta:
            model = Plan
            fields = "__all__"

    if plan_id:
        plan = get_object_or_404(Plan, id=plan_id)
    else:
        plan = None

    if request.method == "POST":
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Plan saved.")
            return redirect("subscriptions-plans")
    else:
        form = PlanForm(instance=plan)

    return render(request, "subscriptions/plan_form.html", {"form": form, "plan": plan})
