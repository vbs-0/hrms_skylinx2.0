"""
Single source of truth for gateable (paid) modules.

key -> {label, prefixes (URL paths to lock), app (sidebar module label)}

Core modules (employee, attendance basics, leave, dashboard, settings) are
always available and intentionally NOT listed here. Anything listed is gated by
the company's subscription: if the feature key isn't in the plan, the URL is
blocked and the sidebar entry is hidden.
"""

PAID_FEATURES = {
    "pms": {"label": "Performance (PMS)", "prefixes": ["/pms/"], "app": "pms"},
    "recruitment": {
        "label": "Recruitment / ATS",
        "prefixes": ["/recruitment/", "/onboarding/"],
        "app": "recruitment",
    },
    "payroll": {"label": "Payroll", "prefixes": ["/payroll/"], "app": "payroll"},
    "project": {
        "label": "Project Management",
        "prefixes": ["/project/"],
        "app": "project",
    },
    "asset": {"label": "Asset Management", "prefixes": ["/asset/"], "app": "asset"},
    "helpdesk": {"label": "Helpdesk", "prefixes": ["/helpdesk/"], "app": "helpdesk"},
    "biometric": {
        "label": "Biometric / Face Attendance",
        "prefixes": ["/biometric/"],
        "app": "biometric",
    },
    # Attendance sub-features: flag-only (no module URL / sidebar entry). Checked
    # via subscription.has_feature(<key>) inside attendance flows (mobile
    # live-location, selfie login, geofence enforcement). prefixes=[] so
    # feature_for_path never blocks a URL; app=None so no sidebar item is added.
    "geofencing": {"label": "Geo-fencing", "prefixes": [], "app": None},
    "live_location": {"label": "Live Location Tracking", "prefixes": [], "app": None},
    "selfie_login": {"label": "Selfie Login", "prefixes": [], "app": None},
}

ALL_FEATURE_KEYS = list(PAID_FEATURES.keys())

# sidebar app label -> feature key, for fast nav filtering. Skip flag-only
# features (app is None) so they don't collide on a shared None key.
APP_TO_FEATURE = {
    meta["app"]: key for key, meta in PAID_FEATURES.items() if meta.get("app")
}


def feature_for_path(path):
    """Return the feature key that owns *path*, or None if it isn't gated."""
    for key, meta in PAID_FEATURES.items():
        for prefix in meta["prefixes"]:
            if path.startswith(prefix):
                return key
    return None
