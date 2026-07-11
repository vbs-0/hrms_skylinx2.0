from django.urls import path
from skylinx_api.api_views.employee.mobile_views import (
    MobileEmployeeDirectoryAPIView,
    MobileOrgChartAPIView,
    MobileOwnProfileAPIView,
    MobileProfilePhotoAPIView,
)

urlpatterns = [
    path("directory/", MobileEmployeeDirectoryAPIView.as_view(), name="mobile-employee-directory"),
    path("org-chart/", MobileOrgChartAPIView.as_view(), name="mobile-org-chart"),
    path("profile-photo/", MobileProfilePhotoAPIView.as_view(), name="mobile-profile-photo"),
    path("profile/", MobileOwnProfileAPIView.as_view(), name="mobile-own-profile"),
]
