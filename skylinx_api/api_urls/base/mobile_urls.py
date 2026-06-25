from django.urls import path
from skylinx_api.api_views.base.mobile_views import MobileAnnouncementsAPIView

urlpatterns = [
    path("announcements/", MobileAnnouncementsAPIView.as_view(), name="mobile-announcements"),
]
