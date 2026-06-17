"""
Client-side subscription dashboard (super-admin only).

Shows the customer their plan, status, expiry + days remaining, employee usage
against the cap, and which paid features are active. Lets them paste/activate a
key and sync with the vendor server. Vendor-side Plan/License management lives
in Django admin (server role).
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import service
from .features import PAID_FEATURES
from .models import LicenseConfig

superadmin_required = user_passes_test(lambda u: u.is_active and u.is_superuser)


@superadmin_required
def subscription(request):
    cfg = LicenseConfig.get()
    state = service.get_state(request)
    limit = state["employee_limit"]
    used = service.active_employee_count()

    features = [
        {
            "key": key,
            "label": meta["label"],
            "enabled": key in state["features"],
        }
        for key, meta in PAID_FEATURES.items()
    ]

    context = {
        "cfg": cfg,
        "licensed": state["licensed"],
        "expired": state["expired"],
        "employee_used": used,
        "employee_limit": limit,
        "employee_pct": (round(used / limit * 100) if limit else None),
        "days_remaining": cfg.days_remaining,
        "features": features,
    }
    return render(request, "licensing/subscription.html", context)


@superadmin_required
@require_POST
def activate(request):
    key = (request.POST.get("license_key") or "").strip()
    cfg = LicenseConfig.get()
    cfg.license_key = key
    cfg.save(update_fields=["license_key"])
    if key:
        ok, msg = service_sync()
        (messages.success if ok else messages.error)(request, msg)
    else:
        messages.info(request, "License key cleared.")
    return redirect("license-subscription")


@superadmin_required
@require_POST
def sync_now(request):
    ok, msg = service_sync()
    (messages.success if ok else messages.error)(request, msg)
    return redirect("license-subscription")


def service_sync():
    """Run the sync command in-process; return (ok, message)."""
    from .sync import sync_license

    return sync_license()
