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
    # AI assistant widget visibility — enabled platform-wide AND allowed for
    # this user's role. Server-side gate; the widget only appears when usable.
    ai_widget_visible = False
    try:
        from subscriptions.models import AISettings
        from base.rbac import org_rank, CEO_RANK, HR_MANAGER_RANK

        cfg = AISettings.load()
        if cfg.enabled and cfg.api_key and getattr(request, "user", None) \
                and request.user.is_authenticated:
            rank = org_rank(request.user)
            if rank <= CEO_RANK:
                ai_widget_visible = cfg.allow_ceo
            elif rank == HR_MANAGER_RANK:
                ai_widget_visible = cfg.allow_hr
            else:
                ai_widget_visible = cfg.allow_employee
            # Plan gating: chatbot is a paid feature — hide the widget when
            # the company's plan lacks it. Platform owner (no subscription of
            # their own) keeps access to administer/test.
            from base.rbac import is_platform_owner

            if ai_widget_visible and not is_platform_owner(request.user):
                ai_widget_visible = "ai_assistant" in (feats or [])
    except Exception:
        ai_widget_visible = False

    return {
        "company_features": feats,
        "company_subscription": sub,
        "trial_days_left": trial_days_left,
        "seat_limit": seat_limit,
        "seat_used": seat_used,
        "seat_left": seat_left,
        "ai_widget_visible": ai_widget_visible,
    }
