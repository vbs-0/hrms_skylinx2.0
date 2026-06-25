"""
Template helpers to hide locked modules.

Usage in a template:
    {% load subscription_tags %}
    {% if "pms"|feature_enabled:request %} ...sidebar link... {% endif %}
    {% if request|app_enabled:"recruitment" %} ... {% endif %}
"""

from django import template

from subscriptions.features import APP_TO_FEATURE

register = template.Library()


@register.filter
def feature_enabled(feature_key, request):
    """True if the current company has this feature key unlocked."""
    return feature_key in getattr(request, "company_features", []) or False


@register.filter
def app_enabled(request, app_label):
    """
    True if the sidebar module (app label) is available. Apps that aren't gated
    are always available.
    """
    key = APP_TO_FEATURE.get(app_label)
    if key is None:
        return True  # not a paid module -> always on
    return key in getattr(request, "company_features", [])
