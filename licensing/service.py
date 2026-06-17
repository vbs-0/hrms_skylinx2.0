"""
Entitlement resolution — the ONE place that decides what is unlocked.

Fail-open by design until a real license is applied, so the vendor's own box
and fresh/unactivated installs keep working. Enforcement only bites once a
client instance has an actual license_key AND it has expired or been revoked.
"""

from django.conf import settings

from .features import ALL_FEATURE_KEYS


def _role():
    return getattr(settings, "LICENSE_ROLE", "client")


def get_state(request=None):
    """
    Return a dict: {features: set, employee_limit: int|None, expired: bool,
    licensed: bool, config: LicenseConfig|None}.

    Cached on the request to avoid re-querying per template tag / middleware.
    """
    if request is not None and hasattr(request, "_license_state"):
        return request._license_state

    state = _resolve()
    if request is not None:
        request._license_state = state
    return state


def _resolve():
    # Vendor instance: everything on, no caps.
    if _role() == "server":
        return {
            "features": set(ALL_FEATURE_KEYS),
            "employee_limit": None,
            "expired": False,
            "licensed": False,
            "config": None,
        }

    from .models import LicenseConfig

    cfg = LicenseConfig.get()

    # Unactivated / dev install — permissive until a key is applied.
    if not cfg.license_key:
        return {
            "features": set(ALL_FEATURE_KEYS),
            "employee_limit": None,
            "expired": False,
            "licensed": False,
            "config": cfg,
        }

    # Licensed client — enforce.
    expired = cfg.is_expired or cfg.status != "active"
    features = set() if expired else set(cfg.enabled_features or [])
    return {
        "features": features,
        "employee_limit": cfg.employee_limit,
        "expired": expired,
        "licensed": True,
        "config": cfg,
    }


def is_feature_enabled(key, request=None):
    return key in get_state(request)["features"]


def is_expired(request=None):
    return get_state(request)["expired"]


def employee_limit(request=None):
    return get_state(request)["employee_limit"]


def active_employee_count():
    """
    Count only enabled/active employees — disabled employees do not count
    toward the license cap (per the licensing design).
    """
    from employee.models import Employee

    return Employee.objects.filter(is_active=True).count()


def employee_cap_reached(request=None):
    """True if adding/enabling another active employee would exceed the cap."""
    limit = employee_limit(request)
    if limit is None:
        return False
    return active_employee_count() >= limit
