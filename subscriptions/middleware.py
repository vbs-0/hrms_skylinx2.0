"""
Per-company subscription enforcement.

For every authenticated, non-superuser request:
  * resolve the user's company -> its subscription
  * if the subscription isn't live (expired / suspended / cancelled / missing)
    -> redirect to the "subscription inactive" page
  * if the URL belongs to a paid module the plan doesn't include
    -> redirect to the "feature locked" page

Superusers (platform owners) bypass everything. The attached
``request.company_features`` is read by the context processor / sidebar to hide
locked modules.
"""

from django.shortcuts import redirect
from django.urls import reverse

from .features import feature_for_path
from .utils import company_for_user, features_for_request, subscription_for_company

# never gated, whatever the subscription state
EXEMPT_PREFIXES = (
    "/login",
    "/logout",
    "/accounts/",
    "/static/",
    "/media/",
    "/i18n/",
    "/django-admin/",
    "/manage/",  # the platform-owner console
    "/subscription/",  # the blocked / locked pages themselves
)


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company_features = []
        user = getattr(request, "user", None)
        path = request.path

        if not (user and user.is_authenticated):
            return self.get_response(request)

        # platform owner sees everything, never blocked
        if user.is_superuser:
            request.company_features = features_for_request(request)
            return self.get_response(request)

        request.company_features = features_for_request(request)

        if path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        sub = subscription_for_company(company_for_user(user))

        # No subscription row yet => don't lock out (fail open for safety).
        if sub is None:
            return self.get_response(request)

        if not sub.is_live:
            return redirect(reverse("subscription-inactive"))

        key = feature_for_path(path)
        if key and key not in request.company_features:
            return redirect(reverse("feature-locked") + f"?f={key}")

        return self.get_response(request)
