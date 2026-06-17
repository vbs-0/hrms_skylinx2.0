"""
Entitlement resolution — the ONE place that decides what is unlocked.

Fail-CLOSED for paid features on a client: an unactivated install runs the core
HRMS but keeps the 7 paid features locked until a valid license enables them.
Only LICENSE_ROLE=server stays fully open (dev/vendor box).
"""

from django.conf import settings

from .features import ALL_FEATURE_KEYS


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

    from .models import LicenseConfig

    cfg = LicenseConfig.get()

    # Unactivated install. Fail-CLOSED on a client: the core HRMS works but the
    # paid features stay locked until a valid license enables them. Only a box
    # explicitly running as the vendor 'server' keeps everything open (dev).
    if not cfg.license_key:
        server = getattr(settings, "LICENSE_ROLE", "client") == "server"
        return {
            "features": set(ALL_FEATURE_KEYS) if server else set(),
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
