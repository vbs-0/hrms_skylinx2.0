from django.apps import AppConfig


class OnboardingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "onboarding"

    def ready(self):
        from django.urls import include, path

        from skylinx.skylinx_settings import APPS
        from skylinx.urls import urlpatterns

        APPS.append("onboarding")
        urlpatterns.append(
            path("onboarding/", include("onboarding.urls")),
        )
        super().ready()
