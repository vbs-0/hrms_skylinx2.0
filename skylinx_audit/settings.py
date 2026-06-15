"""
skylinx_audit/settings.py

This module is used to write settings contents related to payroll app
"""

from skylinx.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "skylinx_audit.context_processors.history_form",
)
