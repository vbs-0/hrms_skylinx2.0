"""
App configuration for the Skylinx Automations app.
Initializes model choices and starts automation when the server runs.
"""

import os
import sys

from django.apps import AppConfig


class SkylinxAutomationConfig(AppConfig):
    """Configuration class for the Skylinx Automations Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "skylinx_automations"

    verbose_name = "Automations"

    def ready(self) -> None:
        ready = super().ready()
        if any(
            cmd in sys.argv
            for cmd in [
                "makemigrations",
                "migrate",
                "compilemessages",
                "flush",
                "shell",
                "test",
            ]
        ):
            return ready
        try:

            from base.templatetags.skylinxfilters import app_installed
            from employee.models import Employee
            from skylinx_automations.methods.methods import get_related_models
            from skylinx_automations.models import MODEL_CHOICES

            recruitment_installed = False
            if app_installed("recruitment"):
                recruitment_installed = True

            models = [Employee]
            if recruitment_installed:
                from recruitment.models import Candidate

                models.append(Candidate)

            main_models = models
            for main_model in main_models:
                related_models = get_related_models(main_model)

                for model in related_models:
                    path = f"{model.__module__}.{model.__name__}"
                    MODEL_CHOICES.append((path, model.__name__))
            MODEL_CHOICES.append(("employee.models.Employee", "Employee"))
            MODEL_CHOICES.append(
                ("pms.models.EmployeeKeyResult", "Employee Key Results")
            )

            MODEL_CHOICES = list(set(MODEL_CHOICES))
            try:
                from skylinx_automations.signals import start_automation

                start_automation()
            except Exception as e:
                print(e)
                """
                Migrations are not affected yet
                """
        except:
            """
            Models not ready yet
            """
        return ready
