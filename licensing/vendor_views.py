"""
Vendor dashboard (server role only) — plans, license generation, tracking.

Gated by both LICENSE_ROLE == "server" and superuser, so this UI never appears
on a customer (client) instance.
"""

import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .features import PAID_FEATURES
from .models import License, Plan

PERIOD_DAYS = {"weekly": 7, "monthly": 30, "yearly": 365}


def _require_vendor(request):
    if getattr(settings, "LICENSE_ROLE", "client") != "server":
        raise PermissionDenied("Vendor dashboard is only available in server mode.")
    if not (request.user.is_active and request.user.is_superuser):
        raise PermissionDenied("Superuser only.")


def dashboard(request):
    _require_vendor(request)
    today = timezone.localdate()
    licenses = License.objects.select_related("plan").order_by("-created_at")

    # Keep statuses honest before we render the tracking table.
    for lic in licenses:
        if lic.status == "active" and lic.is_expired:
            lic.status = "expired"
            lic.save(update_fields=["status"])

    active = licenses.filter(status="active")
    revenue = licenses.aggregate(total=Sum("amount_paid"))["total"] or 0
    expiring = active.filter(expires_on__lte=today + timedelta(days=14)).count()

    context = {
        "plans": Plan.objects.all().order_by("price"),
        "licenses": licenses,
        "new_license_key": request.session.pop("new_license_key", None),
        "feature_choices": [(k, v["label"]) for k, v in PAID_FEATURES.items()],
        "stats": {
            "total": licenses.count(),
            "active": active.count(),
            "revenue": revenue,
            "expiring": expiring,
        },
    }
    return render(request, "licensing/vendor_dashboard.html", context)


@require_POST
def plan_create(request):
    _require_vendor(request)
    name = (request.POST.get("name") or "").strip()
    if not name:
        messages.error(request, "Plan name is required.")
        return redirect("license-vendor")

    try:
        price = Decimal(request.POST.get("price") or "0")
    except InvalidOperation:
        price = Decimal("0")

    limit_raw = (request.POST.get("employee_limit") or "").strip()
    employee_limit = int(limit_raw) if limit_raw.isdigit() else None

    Plan.objects.create(
        name=name,
        billing_period=request.POST.get("billing_period", "monthly"),
        price=price,
        employee_limit=employee_limit,
        features=request.POST.getlist("features"),
    )
    messages.success(request, f"Plan '{name}' created.")
    return redirect("license-vendor")


@require_POST
def license_generate(request):
    _require_vendor(request)
    plan = Plan.objects.filter(pk=request.POST.get("plan")).first()
    if not plan:
        messages.error(request, "Pick a valid plan.")
        return redirect("license-vendor")

    customer = (request.POST.get("customer_name") or "").strip()
    if not customer:
        messages.error(request, "Customer name is required.")
        return redirect("license-vendor")

    try:
        discount = Decimal(request.POST.get("discount_percent") or "0")
    except InvalidOperation:
        discount = Decimal("0")

    # Expiry: explicit date wins, else derived from the plan's billing period.
    expires_on = request.POST.get("expires_on") or None
    if not expires_on:
        days = PERIOD_DAYS.get(plan.billing_period, 30)
        expires_on = timezone.localdate() + timedelta(days=days)

    amount = (plan.price * (Decimal("100") - discount) / Decimal("100")).quantize(
        Decimal("0.01")
    )

    lic = License.objects.create(
        key=secrets.token_urlsafe(32),
        customer_name=customer,
        customer_email=(request.POST.get("customer_email") or "").strip(),
        plan=plan,
        employee_limit=plan.employee_limit,
        features=list(plan.features or []),
        expires_on=expires_on,
        discount_percent=discount,
        amount_paid=amount,
        notes=(request.POST.get("notes") or "").strip(),
    )
    messages.success(request, f"License generated for {customer}.")
    # Surface the key once, prominently.
    request.session["new_license_key"] = lic.key
    return redirect("license-vendor")
