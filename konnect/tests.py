import io
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from base.models import Company
from employee.models import Employee, EmployeeWorkInformation
from notifications.models import Notification


User = get_user_model()


def make_employee(name, company, active=True):
    user = User.objects.create_user(username=name.lower(), password="test-pass")
    employee = Employee.objects.create(
        employee_user_id=user,
        employee_first_name=name,
        employee_last_name="Test",
        email=f"{name.lower()}@test.local",
        phone=f"90000000{user.pk:02d}",
        is_active=active,
    )
    EmployeeWorkInformation.objects.update_or_create(
        employee_id=employee, defaults={"company_id": company}
    )
    return employee


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class KonnectFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company="TestCo", address="x", country="x", city="x", zip="1"
        )
        cls.other_company = Company.objects.create(
            company="OtherCo", address="x", country="x", city="x", zip="2"
        )
        cls.author = make_employee("Author", cls.company)
        cls.recipient = make_employee("Recipient", cls.company)
        cls.inactive = make_employee("Inactive", cls.company, active=False)
        cls.outsider = make_employee("Outsider", cls.other_company)

    def setUp(self):
        self.client.force_login(self.author.employee_user_id)

    def test_post_notifies_only_active_company_colleagues(self):
        response = self.client.post(
            "/api/v1/konnect/feed/", {"body": "Company update"}
        )
        self.assertEqual(response.status_code, 201)
        notification = Notification.objects.get(recipient=self.recipient.employee_user_id)
        self.assertIn("posted in Buzz", notification.verb)
        self.assertEqual(notification.data["redirect"], "/konnect/")
        self.assertFalse(Notification.objects.filter(recipient=self.author.employee_user_id).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.inactive.employee_user_id).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.outsider.employee_user_id).exists())

    def test_uploaded_media_is_returned_and_web_renderer_uses_media_array(self):
        image = Image.new("RGB", (4, 4), "red")
        data = io.BytesIO()
        image.save(data, "PNG")
        upload = SimpleUploadedFile("photo.png", data.getvalue(), content_type="image/png")
        response = self.client.post(
            "/api/v1/konnect/feed/", {"body": "Photo post", "images": upload}
        )
        self.assertEqual(response.status_code, 201)
        payload = self.client.get("/api/v1/konnect/feed/").json()["results"][0]
        self.assertEqual(payload["media"][0]["kind"], "image")
        self.assertTrue(payload["media"][0]["url"].endswith(".webp"))
        self.assertContains(self.client.get("/konnect/"), "function renderMedia(p)")
