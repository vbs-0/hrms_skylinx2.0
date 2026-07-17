from django.db import models

from base.models import Company


class CompanyProfile(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="profile")
    brand_name = models.CharField(max_length=100, blank=True)
    official_email = models.EmailField(blank=True)
    official_contact = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    domain_name = models.CharField(max_length=120, blank=True)
    industry_type = models.CharField(max_length=120, blank=True)
    entity_type = models.CharField(max_length=80, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    cin = models.CharField(max_length=40, blank=True)
    pan = models.CharField(max_length=20, blank=True)
    tan = models.CharField(max_length=20, blank=True)
    gst = models.CharField(max_length=30, blank=True)
    linkedin = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    directors = models.JSONField(default=list, blank=True)
    auditors = models.JSONField(default=list, blank=True)
    company_secretaries = models.JSONField(default=list, blank=True)


class CompanyAddress(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="profile_addresses")
    title = models.CharField(max_length=80)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    pincode = models.CharField(max_length=20, blank=True)


class CompanyBankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="profile_bank_accounts")
    account_title = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=80, blank=True)
    branch_name = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, blank=True)
    ifsc_code = models.CharField(max_length=30, blank=True)
    account_type = models.CharField(max_length=40, blank=True)
    corporate_id = models.CharField(max_length=80, blank=True)
