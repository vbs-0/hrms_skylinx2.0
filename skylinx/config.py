"""
skylinx/config.py

EMPLINX app configurations
"""

import importlib
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.core.cache import cache

logger = logging.getLogger(__name__)


def bump_sidebar_gen(user_id):
    """Invalidate every cached sidebar variant for a user (any feature-hash)."""
    try:
        cache.set(
            f"sidebar_gen_{user_id}",
            (cache.get(f"sidebar_gen_{user_id}", 0) or 0) + 1,
            timeout=None,
        )
    except Exception:
        pass


def get_apps_in_base_dir():
    return settings.SIDEBARS


def import_method(accessibility):
    module_path, method_name = accessibility.rsplit(".", 1)
    module = __import__(module_path, fromlist=[method_name])
    accessibility_method = getattr(module, method_name)
    return accessibility_method


def generate_sidebar(request):
    base_dir_apps = get_apps_in_base_dir()
    MENUS = []

    if not request.user.is_anonymous:
        for app in base_dir_apps:
            if apps.is_installed(app):
                # Licensing: hide nav for paid features this instance can't use.
                from licensing.features import APP_TO_FEATURE
                from licensing import service as _lic

                feature_key = APP_TO_FEATURE.get(app)
                if feature_key and not _lic.is_feature_enabled(feature_key, request):
                    continue

                # Per-company subscription: hide modules the client's plan doesn't
                # include (superuser sees everything). Keeps the sidebar in sync
                # with what the owner set on /manage.
                if not request.user.is_superuser:
                    from subscriptions.features import APP_TO_FEATURE as _SUB_FEAT
                    sub_key = _SUB_FEAT.get(app)
                    if sub_key and sub_key not in getattr(
                        request, "company_features", []
                    ):
                        continue
                try:
                    sidebar = importlib.import_module(app + ".sidebar")

                except Exception as e:
                    logger.error(e)
                    continue

                if sidebar:
                    accessibility = None
                    if getattr(sidebar, "ACCESSIBILITY", None):
                        accessibility = import_method(sidebar.ACCESSIBILITY)

                    if hasattr(sidebar, "MENU") and (
                        not accessibility
                        or accessibility(
                            request,
                            sidebar.MENU,
                            PermWrapper(request.user),
                        )
                    ):
                        MENU = {}
                        MENU["menu"] = sidebar.MENU
                        MENU["app"] = app
                        MENU["img_src"] = sidebar.IMG_SRC
                        MENU["locked"] = getattr(sidebar, "LOCKED", False)
                        MENU["submenu"] = []
                        MENUS.append(MENU)
                        for submenu in sidebar.SUBMENUS:

                            accessibility = None

                            if submenu.get("accessibility"):
                                accessibility = import_method(submenu["accessibility"])
                            redirect: str = submenu["redirect"]
                            redirect = redirect.split("?")
                            submenu["redirect"] = redirect[0]

                            if not accessibility or accessibility(
                                request,
                                submenu,
                                PermWrapper(request.user),
                            ):
                                MENU["submenu"].append(submenu)

        # EMPLINX: explicit module ordering for the main navigation
        SIDEBAR_ORDER = [
            "employee", "recruitment", "onboarding", "attendance", "leave",
            "payroll", "project", "asset", "helpdesk", "offboarding",
            "report", "pms",
        ]
        order_index = {app: i for i, app in enumerate(SIDEBAR_ORDER)}
        MENUS.sort(key=lambda m: order_index.get(m.get("app"), len(SIDEBAR_ORDER)))

        # Append Holiday Calendar main module (evaluate reverse dynamically to be safe for cache)
        from django.urls import reverse
        from django.utils.translation import gettext_lazy as _
        holiday_menu = {
            "menu": _("Holiday Calendar"),
            "app": "holiday_calendar",
            "img_src": "images/ui/dashboard.svg",
            "locked": False,
            "submenu": [
                {
                    "menu": _("View Calendar"),
                    "redirect": reverse("holiday-calendar-view"),
                }
            ]
        }
        MENUS.append(holiday_menu)

    return MENUS


def get_MENUS(request):
    if not request.user.is_authenticated:
        return {"sidebar": []}

    # Cache key includes the company's feature set, so changing a plan on /manage
    # busts the menu immediately instead of waiting out the TTL.
    feats = "".join(sorted(getattr(request, "company_features", []) or []))
    # ponytail: generation counter makes invalidation work despite the feats-hash
    # suffix — bump_sidebar_gen() orphans every variant key for a user at once.
    gen = cache.get(f"sidebar_gen_{request.user.id}", 0)
    cache_key = f"sidebar_menus_user_{request.user.id}_{gen}_{hash(feats)}"
    sidebar_menus = cache.get(cache_key)

    if sidebar_menus is None:
        sidebar_menus = generate_sidebar(request)
        # 120s meant a full sidebar rebuild every 2 min; invalidation now works
        # (generation bump on perm/feature change), so 1h is safe.
        cache.set(cache_key, sidebar_menus, timeout=3600)

    return {"sidebar": sidebar_menus}


def load_ldap_settings():
    """
    Fetch LDAP settings dynamically from the database after Django is ready.
    """
    try:
        from django.db import connection

        from skylinx_ldap.models import LDAPSettings

        # Ensure DB is ready before querying
        if not connection.introspection.table_names():
            print("⚠️ Database is empty. Using default LDAP settings.")
            return settings.DEFAULT_LDAP_CONFIG

        ldap_config = LDAPSettings.objects.first()
        if ldap_config:
            return {
                "LDAP_SERVER": ldap_config.ldap_server,
                "BIND_DN": ldap_config.bind_dn,
                "BIND_PASSWORD": ldap_config.bind_password,
                "BASE_DN": ldap_config.base_dn,
            }
    except Exception as e:
        print(f"⚠️ Warning: Could not load LDAP settings ({e})")
        return settings.DEFAULT_LDAP_CONFIG  # Return default on error

    return settings.DEFAULT_LDAP_CONFIG  # Fallback in case of an issue
