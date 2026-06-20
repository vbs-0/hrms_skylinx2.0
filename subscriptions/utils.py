"""Helpers to resolve a request's company + subscription, and seat checks."""

from .features import ALL_FEATURE_KEYS


def company_for_user(user):
    """Return the Company a (non-superuser) user belongs to, or None."""
    try:
        return user.employee_get.employee_work_info.company_id
    except Exception:
        return None


def subscription_for_company(company):
    if not company:
        return None
    return getattr(company, "subscription", None)


def subscription_for_request(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    return subscription_for_company(company_for_user(user))


def features_for_request(request):
    """
    Feature keys available on this request.

    Superusers (platform owners) get everything. Clients get whatever their
    subscription's plan grants.
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated and user.is_superuser:
        return list(ALL_FEATURE_KEYS)
    sub = subscription_for_request(request)
    return sub.feature_keys() if sub else []


def can_add_employee(company):
    """(ok, message) — whether the company has a free seat."""
    sub = subscription_for_company(company)
    if not sub:
        return True, ""  # no subscription configured => don't block
    avail = sub.seats_available()
    if avail is None:
        return True, ""  # unlimited
    if avail <= 0:
        return (
            False,
            f"Seat limit reached ({sub.seat_limit}). Upgrade the plan to add more employees.",
        )
    return True, ""
