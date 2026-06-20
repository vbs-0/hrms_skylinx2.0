from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "billing_cycle", "seat_limit", "is_active")
    list_filter = ("billing_cycle", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "plan", "status", "expires_on", "trial_ends_on")
    list_filter = ("status", "plan")
    search_fields = ("company__company",)
    autocomplete_fields = ()
