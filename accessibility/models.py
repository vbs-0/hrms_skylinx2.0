"""
accessibility/models.py
"""

from django.db import models
from base.skylinx_company_manager import SkylinxCompanyManager

from accessibility.accessibility import ACCESSBILITY_FEATURE
from employee.models import Employee
from skylinx.models import SkylinxModel


class DefaultAccessibility(SkylinxModel):
    """
    DefaultAccessibilityModel
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    feature = models.CharField(max_length=100, choices=ACCESSBILITY_FEATURE)
    filter = models.JSONField()
    exclude_all = models.BooleanField(default=False)
    employees = models.ManyToManyField(
        Employee, blank=True, related_name="default_accessibility"
    )
    is_enabled = models.BooleanField(default=True)
