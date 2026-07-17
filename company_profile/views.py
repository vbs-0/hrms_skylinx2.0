from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from base.rbac import current_company, is_platform_owner
from base.models import Company

from .forms import CompanyAddressForm, CompanyBankAccountForm, CompanyProfileForm, HRAdminOnboardingForm
from .models import CompanyAddress, CompanyBankAccount, CompanyProfile


def _can_manage(request, company):
    if is_platform_owner(request.user):
        return True
    employee = getattr(request.user, "employee_get", None)
    own = getattr(getattr(employee, "employee_work_info", None), "company_id", None)
    return own and own.pk == company.pk and (
        request.user.has_perm("base.change_company") or request.user.groups.filter(name="Company Admin").exists()
    )


@login_required
def profile(request):
    company = current_company(request) or getattr(getattr(request.user, "employee_get", None), "get_company", lambda: None)()
    if not company:
        return render(request, "company_profile/empty.html")
    profile_obj, _ = CompanyProfile.objects.get_or_create(company=company)
    if request.method == "POST":
        if not _can_manage(request, company):
            return redirect("company-profile")
        form = CompanyProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated.")
            return redirect("company-profile")
    else:
        form = CompanyProfileForm(instance=profile_obj)
    tabs = [
        ("Overview", "company-profile"), ("Address", "company-profile-address"),
        ("Employee Custom Fields", "employee-view"), ("Department", "department-view"),
        ("Designation", "job-position-view"), ("Announcements", "announcement-list"),
        ("Policies", "view-policies"), ("Admin", "company-profile-admin"),
        ("Statutory", "company-profile"), ("My Plan", "subscription-plans"),
    ]
    return render(request, "company_profile/profile.html", {"company": company, "profile": profile_obj, "form": form, "tabs": tabs, "can_manage": _can_manage(request, company)})


@login_required
def addresses(request):
    company = current_company(request)
    if not company:
        return render(request, "company_profile/empty.html")
    address = CompanyAddress.objects.filter(company=company).first()
    if request.method == "POST":
        if not _can_manage(request, company):
            return redirect("company-profile-address")
        form = CompanyAddressForm(request.POST, instance=address)
        if form.is_valid():
            obj = form.save(commit=False); obj.company = company; obj.save()
            return redirect("company-profile-address")
    else:
        form = CompanyAddressForm(instance=address)
    return render(request, "company_profile/addresses.html", {"company": company, "address": address, "form": form, "can_manage": _can_manage(request, company)})


@login_required
def admin_onboarding(request):
    company = current_company(request)
    if not company or not _can_manage(request, company):
        return redirect("company-profile")
    form = HRAdminOnboardingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.create_admin(company)
        messages.success(request, "HR Admin created. They can sign in with the supplied email and temporary password.")
        return redirect("company-profile-admin")
    return render(request, "company_profile/admin.html", {"company": company, "form": form})
