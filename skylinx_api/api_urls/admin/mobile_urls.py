from django.urls import path
from skylinx_api.api_views.admin.mobile_views import (
    MobileAdminAttendanceSummaryAPIView,
    MobileAdminAlertsAPIView,
    MobileAdminMarkAlertReadAPIView,
    MobileAdminMarkAllAlertsReadAPIView,
    MobileAdminSelfieFeedAPIView,
    MobileAdminLocationMapAPIView,
    MobileAdminDailyReportAPIView,
    MobileAdminExportCsvAPIView,
    MobileAdminSettingsAPIView
)

urlpatterns = [
    path("attendance-summary/", MobileAdminAttendanceSummaryAPIView.as_view(), name="mobile-admin-summary"),
    path("alerts/", MobileAdminAlertsAPIView.as_view(), name="mobile-admin-alerts"),
    path("alerts/<int:pk>/read/", MobileAdminMarkAlertReadAPIView.as_view(), name="mobile-admin-alert-read"),
    path("alerts/read-all/", MobileAdminMarkAllAlertsReadAPIView.as_view(), name="mobile-admin-alerts-read-all"),
    path("selfie-feed/", MobileAdminSelfieFeedAPIView.as_view(), name="mobile-admin-selfie-feed"),
    path("location-map/", MobileAdminLocationMapAPIView.as_view(), name="mobile-admin-location-map"),
    path("daily-report/", MobileAdminDailyReportAPIView.as_view(), name="mobile-admin-daily-report"),
    path("export-csv/", MobileAdminExportCsvAPIView.as_view(), name="mobile-admin-export-csv"),
    path("settings/", MobileAdminSettingsAPIView.as_view(), name="mobile-admin-settings"),
]
