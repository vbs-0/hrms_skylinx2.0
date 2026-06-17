"""
Vendor-side management via Django admin (server role).

Plans, license generation and tracking all run through admin — the stdlib
answer before building custom CRUD. A custom key is auto-generated on save.
"""

import secrets

from django.contrib import admin

from .models import License, LicenseConfig, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "billing_period", "price", "employee_limit", "is_active")
    list_filter = ("billing_period", "is_active")
    search_fields = ("name",)


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "plan",
        "status",
        "issued_on",
        "expires_on",
        "is_valid",
        "amount_paid",
    )
    list_filter = ("status", "plan", "expires_on")
    search_fields = ("customer_name", "customer_email", "key")
    readonly_fields = ("key", "created_at")

    @admin.display(boolean=True, description="Valid")
    def is_valid(self, obj):
        return obj.is_valid()

    def save_model(self, request, obj, form, change):
        if not obj.key:
            obj.key = secrets.token_urlsafe(32)
        # If a plan is chosen and the snapshot fields are blank, seed them.
        if obj.plan and not obj.features:
            obj.features = list(obj.plan.features or [])
        if obj.plan and obj.employee_limit is None:
            obj.employee_limit = obj.plan.employee_limit
        super().save_model(request, obj, form, change)


@admin.register(LicenseConfig)
class LicenseConfigAdmin(admin.ModelAdmin):
    list_display = ("plan_name", "status", "expires_on", "employee_limit", "last_synced")

    def has_add_permission(self, request):
        # Singleton — only the auto-created pk=1 row.
        return not LicenseConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
