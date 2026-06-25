from django.urls import path
from ...api_views.auth.mobile_auth_views import (
    MobileLoginAPIView,
    MobileProfileAPIView,
    MobilePasswordChangeAPIView
)

urlpatterns = [
    path("login/", MobileLoginAPIView.as_view(), name="mobile-api-login"),
    path("me/", MobileProfileAPIView.as_view(), name="mobile-api-profile"),
    path("change-password/", MobilePasswordChangeAPIView.as_view(), name="mobile-api-change-password"),
]
