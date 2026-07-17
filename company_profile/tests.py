from django.contrib.auth import get_user_model
from django.test import TestCase

from base.models import Company
from employee.models import Employee

from .forms import HRAdminOnboardingForm
from .models import CompanyProfile


class CompanyProfileTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company="Profile Tenant", address="x", country="India", state="TS", city="Hyd", zip="500001"
        )

    def test_profile_is_created_for_company(self):
        profile = CompanyProfile.objects.create(company=self.company, brand_name="Profile Brand")
        self.assertEqual(profile.company, self.company)

    def test_hr_admin_onboarding_assigns_company_admin_group_and_company(self):
        form = HRAdminOnboardingForm(
            {"name": "HR Manager", "email": "hr@example.com", "temporary_password": "temporary-123"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.create_admin(self.company)
        self.assertTrue(user.groups.filter(name="Company Admin").exists())
        employee = Employee.objects.get(employee_user_id=user)
        self.assertEqual(employee.employee_work_info.company_id, self.company)

    def test_hr_admin_onboarding_rejects_duplicate_email(self):
        User = get_user_model()
        User.objects.create_user(username="existing", email="existing@example.com", password="temporary-123")
        form = HRAdminOnboardingForm(
            {"name": "Existing", "email": "existing@example.com", "temporary_password": "temporary-123"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
