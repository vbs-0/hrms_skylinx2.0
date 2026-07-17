from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.rbac import is_platform_owner

MENU = _("Company Profile")
IMG_SRC = "images/ui/dashboard.svg"


def profile_accessibility(request, submenu, user_perms, *args, **kwargs):
    return is_platform_owner(request.user) or bool(getattr(request.user, "employee_get", None))


SUBMENUS = [{"menu": _("Company Profile"), "redirect": reverse_lazy("company-profile"), "accessibility": "company_profile.sidebar.profile_accessibility"}]
