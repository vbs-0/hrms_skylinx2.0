"""
skylinx_automations/filters.py
"""

from skylinx.filters import SkylinxFilterSet, django_filters
from skylinx_automations.models import MailAutomation


class AutomationFilter(SkylinxFilterSet):
    """
    AutomationFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = MailAutomation
        fields = "__all__"
