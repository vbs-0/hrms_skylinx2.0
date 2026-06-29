from django.urls import path
from ...api_views.leave.mobile_views import (
    MobileLeaveApplyAPIView,
    MobileMyLeavesAPIView,
    MobileLeaveSummaryAPIView,
    MobileLeaveCancelAPIView,
    MobileHolidaysAPIView,
    MobileAdminLeaveListAPIView,
    MobileAdminLeaveReviewAPIView,
    MobileAdminHolidayDeleteAPIView,
    MobileAvailableLeaveTypesAPIView
)

urlpatterns = [
    path("", MobileAdminLeaveListAPIView.as_view(), name="mobile-api-admin-leaves-list"),
    path("<int:pk>/review/", MobileAdminLeaveReviewAPIView.as_view(), name="mobile-api-admin-leave-review"),
    path("apply", MobileLeaveApplyAPIView.as_view(), name="mobile-api-leave-apply-no-slash"),
    path("apply/", MobileLeaveApplyAPIView.as_view(), name="mobile-api-leave-apply"),
    path("available-types/", MobileAvailableLeaveTypesAPIView.as_view(), name="mobile-api-available-leave-types"),
    path("my/", MobileMyLeavesAPIView.as_view(), name="mobile-api-my-leaves"),
    path("my/summary/", MobileLeaveSummaryAPIView.as_view(), name="mobile-api-leave-summary"),
    path("<int:pk>/cancel/", MobileLeaveCancelAPIView.as_view(), name="mobile-api-leave-cancel"),
    path("holidays/", MobileHolidaysAPIView.as_view(), name="mobile-api-holidays"),
    path("holidays/<str:pk>/", MobileAdminHolidayDeleteAPIView.as_view(), name="mobile-api-holiday-delete"),
]
