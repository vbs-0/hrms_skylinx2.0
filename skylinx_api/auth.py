"""
Authentication utilities for the API
"""

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class CompanyScopedJWTAuthentication(JWTAuthentication):
    """
    JWT auth that pins the tenant context to the authenticated user's own company.

    Mobile/API requests authenticate AFTER the web CompanySelectionMiddleware has
    already run, so no company is selected in the thread-local context. Without this,
    the SkylinxCompanyManager sees no selected company and a scoped (non-owner) user's
    queries return nothing -> the app shows empty/zeroed data everywhere. We resolve
    the user's OWN company here (platform owner keeps "all"), so scoped `.objects`
    queries work without leaking other tenants' data.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            # Imported lazily to avoid import cycles at settings-load time.
            from skylinx.skylinx_middlewares import set_selected_company
            from base.rbac import is_platform_owner

            try:
                if is_platform_owner(user):
                    set_selected_company("all")
                else:
                    set_selected_company(
                        user.employee_get.employee_work_info.company_id_id
                    )
            except Exception:
                # No employee/work-info -> leave context unset (manager falls back
                # to qs.none() for non-owners, same as before).
                pass
        return result


class SwaggerAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for Swagger UI
    """

    def authenticate(self, request):
        # Get the authentication header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        # Try JWT authentication first
        if auth_header.startswith("Bearer "):
            jwt_auth = JWTAuthentication()
            try:
                return jwt_auth.authenticate(request)
            except:
                pass

        # Fall back to session authentication
        if request.user and request.user.is_authenticated:
            return (request.user, None)

        return None


class RejectBasicAuthentication(authentication.BaseAuthentication):
    """
    Explicitly reject HTTP Basic Auth across the API with a clear error message.
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Basic "):
            raise AuthenticationFailed(
                "Basic authentication is disabled. Use Bearer token (JWT) in the Authorization header."
            )
        return None
