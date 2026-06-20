"""Expose subscription + feature info to every template."""

from .utils import features_for_request, subscription_for_request


def subscription_context(request):
    return {
        "company_features": getattr(
            request, "company_features", None
        )
        or features_for_request(request),
        "company_subscription": subscription_for_request(request),
    }
