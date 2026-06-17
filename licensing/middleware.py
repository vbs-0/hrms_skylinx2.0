"""
License enforcement middleware (client role).

Two gates, cheapest first:
  1. Expired license  -> everything is blocked except the subscription
     dashboard, auth, static/media and the health check (the design doc's
     "only dashboard visible" rule).
  2. Locked feature   -> requests under a paid feature's URL prefix are blocked
     unless that feature is enabled.

Fail-open: when the instance is unlicensed (no key) or role=server, get_state()
returns all-features/no-expiry, so this middleware is a no-op.
"""

from django.shortcuts import redirect
from django.urls import reverse

from . import service
from .features import PAID_FEATURES

# Path prefixes that must stay reachable even when the license is expired.
_ALWAYS_ALLOW = (
    "/license/",
    "/accounts/",
    "/static/",
    "/media/",
    "/admin/",
    "/health/",
    "/i18n/",
    "/jsi18n/",
    "/logout",
)


class LicenseEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not path.startswith(_ALWAYS_ALLOW):
            state = service.get_state(request)

            # Gate 1: expired -> dashboard-only.
            if state["expired"] and not self._is_dashboard(path):
                return self._block(request, expired=True)

            # Gate 2: locked paid feature.
            feature = self._feature_for(path)
            if feature and feature not in state["features"]:
                return self._block(request, feature=feature)

        return self.get_response(request)

    @staticmethod
    def _is_dashboard(path):
        # The dashboard itself lives under /license/, already in _ALWAYS_ALLOW,
        # but the main "/" dashboard must also stay visible when expired.
        return path == "/" or path.startswith("/dashboard")

    @staticmethod
    def _feature_for(path):
        for key, meta in PAID_FEATURES.items():
            for prefix in meta["prefixes"]:
                if path.startswith(prefix):
                    return key
        return None

    def _block(self, request, expired=False, feature=None):
        # htmx/ajax: send a 403 the front-end can surface without a full redirect.
        if request.headers.get("HX-Request") or request.headers.get(
            "x-requested-with"
        ) == "XMLHttpRequest":
            from django.http import HttpResponse

            msg = (
                "Your subscription has expired."
                if expired
                else "This feature is not included in your plan."
            )
            return HttpResponse(msg, status=403)
        return redirect(reverse("license-subscription"))
