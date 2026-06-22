"""Expose subscription + feature info to every template."""

from .utils import features_for_request, subscription_for_request


def subscription_context(request):
    # Middleware sets request.company_features (may legitimately be []).
    # Only recompute if the attribute is genuinely missing — avoids a wasted
    # query and avoids treating an empty (valid) list as "unset".
    feats = getattr(request, "company_features", None)
    if feats is None:
        feats = features_for_request(request)
    return {
        "company_features": feats,
        "company_subscription": subscription_for_request(request),
    }
