from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscriptions"
    verbose_name = "Subscriptions & Tenants"

    def ready(self):
        # registers the daily expiry sweep (gated off in web workers by
        # skylinx.scheduler_guard unless RUN_SCHEDULERS=1)
        from subscriptions import scheduler  # noqa: F401
