from django import template

from licensing import service

register = template.Library()


@register.simple_tag(takes_context=True)
def feature_on(context, key):
    """{% feature_on 'pms' as show %} — True if the feature is licensed."""
    request = context.get("request")
    return service.is_feature_enabled(key, request)
