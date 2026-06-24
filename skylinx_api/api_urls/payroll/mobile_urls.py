from django.urls import path
from skylinx_api.api_views.payroll.mobile_views import (
    MobilePayslipListAPIView,
    MobileExpenseListAPIView,
    MobilePayslipPDFAPIView
)

urlpatterns = [
    path("payslips/", MobilePayslipListAPIView.as_view(), name="mobile-payslips"),
    path("payslips/<int:pk>/pdf/", MobilePayslipPDFAPIView.as_view(), name="mobile-payslip-pdf"),
    path("expenses/", MobileExpenseListAPIView.as_view(), name="mobile-expenses"),
]
