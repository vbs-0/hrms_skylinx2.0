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
from ...api_views.attendance.request_views import (
    MobileAttendanceRequestAPIView,
    MobileAttendanceRequestAdminAPIView,
    MobileMarkPresentAPIView,
    MobileTeamAttendanceStatusAPIView,
    MobileMarkAbsentAPIView,
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
    # ── Attendance approval flow (Kredily-style Get Approval) ────────────
    path("requests/", MobileAttendanceRequestAPIView.as_view(), name="mobile-api-attendance-requests"),
    path("requests/pending/", MobileAttendanceRequestAdminAPIView.as_view(), name="mobile-api-attendance-requests-pending"),
    path("requests/<int:attendance_id>/action/", MobileAttendanceRequestAdminAPIView.as_view(), name="mobile-api-attendance-request-action"),
    path("mark-present/", MobileMarkPresentAPIView.as_view(), name="mobile-api-mark-present"),
    path("mark-absent/", MobileMarkAbsentAPIView.as_view(), name="mobile-api-mark-absent"),
    path("team-status/", MobileTeamAttendanceStatusAPIView.as_view(), name="mobile-api-team-status"),
]
