import json

from django.db import models
from base.skylinx_company_manager import SkylinxCompanyManager

from skylinx.skylinx_middlewares import _thread_locals
from skylinx.models import SkylinxModel
from skylinx_auth.models import SkylinxUser

# Create your models here.


class ToggleColumn(SkylinxModel):
    """
    ToggleColumn
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    user_id = models.ForeignKey(
        SkylinxUser,
        on_delete=models.CASCADE,
        related_name="user_excluded_column",
        editable=False,
    )
    path = models.CharField(max_length=256)
    excluded_columns = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", {})
        user = request.user
        self.user_id = user
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.user_id.employee_get)


class ActiveTab(SkylinxModel):
    """
    ActiveTab
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    path = models.CharField(max_length=256)
    tab_target = models.CharField(max_length=256)


class ActiveGroup(SkylinxModel):
    """
    ActiveGroup
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    path = models.CharField(max_length=256)
    group_target = models.CharField(max_length=256)
    group_by_field = models.CharField(max_length=256)


class SavedFilter(SkylinxModel):
    """
    SavedFilter
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    title = models.CharField(max_length=20, null=True)
    color = models.CharField(max_length=10, default="")
    is_default = models.BooleanField(default=False)
    filter = models.TextField()
    urlencode = models.TextField(default="")
    path = models.CharField(max_length=256)
    referrer = models.CharField(max_length=256, default="")

    xss_exempt_fields = [
        "urlencode",
    ]

    def save(self, *args, **kwargs):
        SavedFilter.objects.filter(
            is_default=True, path=self.path, created_by=self.created_by
        ).exclude(id=self.pk).update(is_default=False)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.title)


class ActiveView(SkylinxModel):
    """
    This model to store the active view type for HNV
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    path = models.CharField(max_length=256)
    type = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class ColumnOrder(SkylinxModel):

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()
    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.CASCADE, related_name="column_order"
    )
    path = models.CharField(max_length=256)
    column_order = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", {})
        employee = request.user.employee_get
        self.employee = employee
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.employee)
