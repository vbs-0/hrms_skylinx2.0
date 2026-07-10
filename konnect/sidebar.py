"""
konnect/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Konnect")
IMG_SRC = "images/ui/comment.png"

SUBMENUS = [
    {
        "menu": _("Company Feed"),
        "redirect": reverse_lazy("konnect-page"),
    },
]
