from django.urls import path
from ...api_views.attendance.mobile_views import (
    MobileCheckInAPIView,
    MobileCheckOutAPIView,
    MobileLocationLogAPIView,
    MobileAttendanceHistoryAPIView
)

urlpatterns = [
    path("check-in/", MobileCheckInAPIView.as_view(), name="mobile-api-check-in"),
    path("check-out/", MobileCheckOutAPIView.as_view(), name="mobile-api-check-out"),
    path("location/", MobileLocationLogAPIView.as_view(), name="mobile-api-location-log"),
    path("my/", MobileAttendanceHistoryAPIView.as_view(), name="mobile-api-history"),
]
