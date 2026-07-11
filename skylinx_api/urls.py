from django.conf import settings
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from skylinx_api.schema import OrderedTagSchemaGenerator
from skylinx_api.api_views.notifications.views import DeviceTokenView

# Create schema view for Swagger and ReDoc
schema_view = get_schema_view(
    openapi.Info(
        title="EMPLINX API",
        default_version="v1",
        description="API documentation for EMPLINX. Click the 'Authorize' button at the top to authenticate.",
        terms_of_service="https://www.emplinx.com/terms/",
        contact=openapi.Contact(email="support@emplinx.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=OrderedTagSchemaGenerator,
)

urlpatterns = [
    # API Documentation URLs
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("docs/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-docs"),
    # API Endpoints (static configuration)
    path("auth/", include("skylinx_api.api_urls.auth.urls")),
    path("asset/", include("skylinx_api.api_urls.asset.urls")),
    path("base/", include("skylinx_api.api_urls.base.urls")),
    path("employee/", include("skylinx_api.api_urls.employee.urls")),
    path("notifications/", include("skylinx_api.api_urls.notifications.urls")),
    path("payroll/", include("skylinx_api.api_urls.payroll.urls")),
    path("attendance/", include("skylinx_api.api_urls.attendance.urls")),
    path("leave/", include("skylinx_api.api_urls.leave.urls")),
    path("helpdesk/", include("skylinx_api.api_urls.helpdesk.urls")),
    path("project/", include("skylinx_api.api_urls.project.urls")),
    path("onboarding/", include("skylinx_api.api_urls.onboarding.urls")),
    path("offboarding/", include("skylinx_api.api_urls.offboarding.urls")),
    path("recruitment/", include("skylinx_api.api_urls.recruitment.urls")),
    path("pms/", include("skylinx_api.api_urls.pms.urls")),
    # --- Mobile API (v1) for the Flutter app ---
    path("v1/auth/", include("skylinx_api.api_urls.auth.mobile_urls")),
    path("v1/attendance/", include("skylinx_api.api_urls.attendance.mobile_urls")),
    path("v1/leaves/", include("skylinx_api.api_urls.leave.mobile_urls")),
    path("v1/payroll/", include("skylinx_api.api_urls.payroll.mobile_urls")),
    path("v1/employee/", include("skylinx_api.api_urls.employee.mobile_urls")),
    path("v1/project/", include("skylinx_api.api_urls.project.urls")),
    path("v1/base/", include("skylinx_api.api_urls.base.mobile_urls")),
    path("v1/admin/", include("skylinx_api.api_urls.admin.mobile_urls")),
    path("v1/notifications/", include("skylinx_api.api_urls.notifications.mobile_urls")),
    path("v1/buzz/", include("buzz.urls_api")),
    path("v1/konnect/", include("konnect.urls_api")),
    # FCM push token registration — the Flutter app posts here on login.
    path("v1/notifications/device-token/", DeviceTokenView.as_view()),
    # Back-compat alias: builds <=1.1.2 have a URL bug that drops the slash
    # after v1, so they POST to /api/v1notifications/device-token/. Accept it
    # here so already-installed apps register for push without a reinstall.
    path("v1notifications/device-token/", DeviceTokenView.as_view()),
]
