from django.urls import path
from ...api_views.attendance.mobile_views import (
    MobileCheckInAPIView,
    MobileCheckOutAPIView,
    MobileLocationLogAPIView,
    MobileAttendanceHistoryAPIView
)
from ...api_views.attendance.shift_request_views import (
    MobileShiftListAPIView,
    MobileShiftRequestAPIView,
    MobileShiftRequestCancelAPIView,
)

urlpatterns = [
    path("check-in/", MobileCheckInAPIView.as_view(), name="mobile-api-check-in"),
    path("check-out/", MobileCheckOutAPIView.as_view(), name="mobile-api-check-out"),
    path("location/", MobileLocationLogAPIView.as_view(), name="mobile-api-location-log"),
    path("my/", MobileAttendanceHistoryAPIView.as_view(), name="mobile-api-history"),
    # ── Shift Request endpoints ──────────────────────────────────────────
    path("shifts/", MobileShiftListAPIView.as_view(), name="mobile-api-shifts-list"),
    path("shift-requests/", MobileShiftRequestAPIView.as_view(), name="mobile-api-shift-requests"),
    path("shift-requests/<int:pk>/cancel/", MobileShiftRequestCancelAPIView.as_view(), name="mobile-api-shift-request-cancel"),
]
