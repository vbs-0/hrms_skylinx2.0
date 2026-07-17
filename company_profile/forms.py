from django import forms
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail

from base.models import Company
from employee.models import Employee, EmployeeWorkInformation
from subscriptions.views import _company_admin_group

from .models import CompanyAddress, CompanyBankAccount, CompanyProfile


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        exclude = ["company"]
        widgets = {"incorporation_date": forms.DateInput(attrs={"type": "date"})}


class CompanyAddressForm(forms.ModelForm):
    class Meta:
        model = CompanyAddress
        exclude = ["company"]


class CompanyBankAccountForm(forms.ModelForm):
    class Meta:
        model = CompanyBankAccount
        exclude = ["company"]


class HRAdminOnboardingForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    temporary_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if get_user_model().objects.filter(email__iexact=email).exists() or Employee.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists for this email.")
        return email

    def create_admin(self, company):
        User = get_user_model()
        first_name, _, last_name = self.cleaned_data["name"].strip().partition(" ")
        user = User.objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["temporary_password"],
            first_name=first_name,
            last_name=last_name,
        )
        user.groups.add(_company_admin_group())
        employee = Employee.objects.create(
            employee_user_id=user,
            employee_first_name=first_name or self.cleaned_data["name"],
            employee_last_name=last_name,
            email=self.cleaned_data["email"],
            phone="9999999999",
        )
        work_info, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=employee)
        work_info.company_id = company
        work_info.save()
        if getattr(settings, "DEFAULT_FROM_EMAIL", ""):
            send_mail(
                "Your Emplinx HR Admin account",
                "You have been onboarded as an HR Admin. Sign in with this email and your temporary password, then change it immediately.",
                settings.DEFAULT_FROM_EMAIL,
                [self.cleaned_data["email"]],
                fail_silently=True,
            )
        return user
