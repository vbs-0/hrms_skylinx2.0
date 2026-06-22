"""Expose subscription + feature info to every template."""

from django.utils import timezone

from .utils import features_for_request, subscription_for_request


def subscription_context(request):
    # Middleware sets request.company_features (may legitimately be []).
    # Only recompute if the attribute is genuinely missing — avoids a wasted
    # query and avoids treating an empty (valid) list as "unset".
    feats = getattr(request, "company_features", None)
    if feats is None:
        feats = features_for_request(request)
    sub = subscription_for_request(request)
    # trial banner (gap #7): days left while on trial, else None
    trial_days_left = None
    if sub and sub.status == "trial" and sub.trial_ends_on:
        trial_days_left = (sub.trial_ends_on - timezone.now().date()).days
    # seat usage banner: surface when a company is at/near its plan's cap
    seat_limit = seat_used = seat_left = None
    if sub:
        seat_limit = sub.seat_limit
        if seat_limit is not None:
            seat_used = sub.seats_used()
            seat_left = max(0, seat_limit - seat_used)
    return {
        "company_features": feats,
        "company_subscription": sub,
        "trial_days_left": trial_days_left,
        "seat_limit": seat_limit,
        "seat_used": seat_used,
        "seat_left": seat_left,
    }
