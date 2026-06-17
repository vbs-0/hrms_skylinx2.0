"""
Vendor-side management via Django admin (server role).

Plans, license generation and tracking all run through admin — the stdlib
answer before building custom CRUD. A custom key is auto-generated on save.
"""

from django.contrib import admin

from .models import LicenseConfig



@admin.register(LicenseConfig)
class LicenseConfigAdmin(admin.ModelAdmin):
    list_display = ("plan_name", "status", "expires_on", "employee_limit", "last_synced")

    def has_add_permission(self, request):
        # Singleton — only the auto-created pk=1 row.
        return not LicenseConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
