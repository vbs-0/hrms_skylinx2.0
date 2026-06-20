"""
Single source of truth for paid features.

Each entry maps a feature `key` to the URL prefixes that belong to it (used by
the enforcement middleware) and the sidebar app label (used to hide nav). Add a
new paid feature here and both enforcement and nav-hiding pick it up — no edits
scattered across apps.
"""

# key -> {label, prefixes (URL paths to lock), app (sidebar module name)}
PAID_FEATURES = {
    "pms": {
        "label": "Performance (PMS)",
        "prefixes": ["/pms/"],
        "app": "pms",
    },
}

ALL_FEATURE_KEYS = list(PAID_FEATURES.keys())

# app (sidebar module) -> feature key, for fast nav filtering
APP_TO_FEATURE = {meta["app"]: key for key, meta in PAID_FEATURES.items()}


def feature_for_path(path):
    """Return the feature key that owns *path*, or None if it's not paywalled."""
    for key, meta in PAID_FEATURES.items():
        for prefix in meta["prefixes"]:
            if path.startswith(prefix):
                return key
    return None
