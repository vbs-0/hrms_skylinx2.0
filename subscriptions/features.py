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
}

ALL_FEATURE_KEYS = list(PAID_FEATURES.keys())

# sidebar app label -> feature key, for fast nav filtering
APP_TO_FEATURE = {meta["app"]: key for key, meta in PAID_FEATURES.items()}


def feature_for_path(path):
    """Return the feature key that owns *path*, or None if it isn't gated."""
    for key, meta in PAID_FEATURES.items():
        for prefix in meta["prefixes"]:
            if path.startswith(prefix):
                return key
    return None
