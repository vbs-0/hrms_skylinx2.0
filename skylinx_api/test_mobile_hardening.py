from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from project.models import TimeSheet
from skylinx_api.api_serializers.project.serializers import TimeSheetSerializer
from skylinx_api.api_views.employee.mobile_views import MobileProfilePhotoAPIView
from skylinx_api.api_views.base.mobile_views import MobileAnnouncementsAPIView
from skylinx_api.api_views.project.views import TimeSheetGetCreateAPIView


class MobileHardeningTests(SimpleTestCase):
    @patch("skylinx_api.api_views.base.mobile_views.notify.send")
    @patch("skylinx_api.api_views.base.mobile_views.SkylinxUser.objects.filter")
    @patch("skylinx_api.api_views.base.mobile_views.Announcement.objects.create")
    def test_mobile_announcement_notifies_active_company_users(
        self, create_announcement, filter_users, send_notification
    ):
        company = SimpleNamespace(pk=7)
        employee = SimpleNamespace(get_company=lambda: company)
        user = SimpleNamespace(
            employee_get=employee,
            has_perm=lambda permission: permission == "base.add_announcement",
            is_authenticated=True,
            is_superuser=False,
        )
        announcement = create_announcement.return_value
        recipients = filter_users.return_value.distinct.return_value
        request = APIRequestFactory().post(
            "/api/v1/base/announcements/",
            {"title": "Mobile announcement", "description": "For everyone"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = MobileAnnouncementsAPIView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        announcement.company_id.add.assert_called_once_with(company)
        filter_users.assert_called_once_with(
            employee_get__employee_work_info__company_id=company,
            employee_get__is_active=True,
            is_active=True,
        )
        send_notification.assert_called_once_with(
            employee,
            recipient=recipients,
            verb="A new announcement was posted.",
            redirect="/announcement-list/",
            icon="chatbox-ellipses",
        )

    def test_profile_photo_accepts_octet_stream_with_image_extension(self):
        employee = MagicMock()
        employee.save.side_effect = lambda **kwargs: setattr(
            employee, "employee_profile", SimpleNamespace(url="/media/profile.jpg")
        )
        request = APIRequestFactory().post(
            "/api/v1/employee/profile-photo/",
            {
                "photo": SimpleUploadedFile(
                    "profile.jpg", b"jpeg", content_type="application/octet-stream"
                )
            },
            format="multipart",
        )
        force_authenticate(
            request,
            user=SimpleNamespace(employee_get=employee, is_authenticated=True),
        )

        response = MobileProfilePhotoAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        employee.save.assert_called_once_with(update_fields=["employee_profile"])

    @patch("skylinx_api.api_views.project.views.TimeSheetSerializer")
    def test_timesheet_forces_authenticated_employee_even_with_add_permission(
        self, serializer
    ):
        serializer.return_value.is_valid.return_value = True
        serializer.return_value.data = {"id": 1}
        employee = SimpleNamespace(pk=10)
        user = SimpleNamespace(
            employee_get=employee,
            has_perm=lambda permission: True,
            is_active=True,
            is_authenticated=True,
        )
        request = APIRequestFactory().post(
            "/api/v1/project/timesheet/",
            {"employee_id_write": 9, "description": "worked"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = TimeSheetGetCreateAPIView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(serializer.call_args.kwargs["data"]["employee_id_write"], 10)

    @patch("skylinx_api.api_views.project.views.TimeSheet.objects.all")
    def test_timesheet_list_is_scoped_to_authenticated_employee(self, all_timesheets):
        queryset = MagicMock()
        all_timesheets.return_value = queryset
        queryset.filter.return_value = queryset
        employee = SimpleNamespace(pk=10)
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))

        result = TimeSheetGetCreateAPIView().get_queryset(request)

        self.assertIs(result, queryset)
        queryset.filter.assert_called_once_with(employee_id=employee)

    @patch.object(TimeSheet, "clean")
    def test_timesheet_serializer_runs_model_membership_validation(self, clean):
        TimeSheetSerializer().validate({"description": "worked"})
        clean.assert_called_once_with()
