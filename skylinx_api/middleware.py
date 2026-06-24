from django.http import JsonResponse


class RejectBasicAuthMiddleware:
    """
    Middleware that rejects HTTP Basic Authentication globally with a consistent message.
    This ensures endpoints that override DRF authentication classes still reject Basic.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if isinstance(auth_header, str) and auth_header.startswith("Basic "):
            return JsonResponse(
                {
                    "error": "Basic authentication is disabled",
                    "detail": "Use Bearer token (JWT) in the Authorization header.",
                },
                status=401,
            )
        return self.get_response(request)


class MobileTenantMiddleware:
    """
    Middleware that reads the authenticated user's company and sets CurrentCompany
    in the thread-local context so SkylinxCompanyManager queries are scoped correctly.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                auth = JWTAuthentication()
                header = auth.get_header(request)
                if header:
                    raw_token = auth.get_raw_token(header)
                    validated_token = auth.get_validated_token(raw_token)
                    user = auth.get_user(validated_token)
                    company = user.employee_get.get_company()
                    if company:
                        from skylinx.skylinx_middlewares import set_selected_company
                        set_selected_company(company)
            except Exception:
                pass

        return self.get_response(request)
