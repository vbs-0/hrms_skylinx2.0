"""
licensing/sidebar.py — main-nav entry.

client role: "Subscription" (customer sees their own plan/usage).
server role: "Licensing" vendor dashboard (plans, generation, tracking).
Both are superuser-only.
"""

from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

IMG_SRC = "images/ui/key.png"

if getattr(settings, "LICENSE_ROLE", "client") == "server":
    MENU = _("Licensing")
    SUBMENUS = [
        {
            "menu": _("Vendor Dashboard"),
            "redirect": reverse_lazy("license-vendor"),
        },
    ]
else:
    MENU = _("Subscription")
    SUBMENUS = [
        {
            "menu": _("My Subscription"),
            "redirect": reverse_lazy("license-subscription"),
        },
    ]

ACCESSIBILITY = "licensing.sidebar.licensing_accessibility"


def licensing_accessibility(request, submenu, user_perms, *args, **kwargs):
    return bool(request.user.is_active and request.user.is_superuser)
