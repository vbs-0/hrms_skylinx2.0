"""
base.py — Main Django settings for EMPLINX
"""

import os
from datetime import timedelta
from os.path import join
from pathlib import Path

import environ
from django.contrib.messages import constants as messages
from django.core.files.storage import FileSystemStorage

# ========================================
# BASE PATH & ENVIRONMENT CONFIGURATION
# ========================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# settings.py
import os

env = environ.Env(
    # Secure-by-default: production must explicitly opt into DEBUG and provide
    # its own SECRET_KEY / ALLOWED_HOSTS via the environment.
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:8000"]),
    # Licensing: "client" (deployed HRMS, enforces entitlements) or "server"
    # (vendor's private instance — all features on, manages Plans/Licenses).
    LICENSE_ROLE=(str, "client"),
    LICENSE_SERVER_URL=(str, ""),
)

env.read_env(os.path.join(BASE_DIR, ".env"), overwrite=True)

# ========================================
# CORE DJANGO SETTINGS
# ========================================
# No insecure fallback: if SECRET_KEY is unset the app fails to start rather
# than silently signing sessions/CSRF tokens with a predictable key.
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
import sys

ALLOWED_HOSTS = env("ALLOWED_HOSTS")
if "test" in sys.argv:
    ALLOWED_HOSTS.append("testserver")
    MIGRATION_MODULES = {"notifications": None}
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Licensing role + vendor server endpoint (see env() defaults above).
LICENSE_ROLE = env("LICENSE_ROLE")
LICENSE_SERVER_URL = env("LICENSE_SERVER_URL")

# ----------------------------------------
# Cookie / transport hardening
# ----------------------------------------
# Always keep session/CSRF cookies out of reach of JS.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # CSRF cookie must be readable by the JS that sends the header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# In production (DEBUG off) require HTTPS for cookies and enable HSTS. Left
# relaxed under DEBUG so local http://localhost development keeps working.
if not DEBUG:
    # ponytail: env-gated so an http-only IP box runs without TLS; True once behind HTTPS
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ponytail: pin default Site so admin/django.contrib.sites works regardless of
# request host (IP, localhost, domain) instead of host-matching the Site table.
SITE_ID = 1

THEME_APP = "skylinx_theme"

INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party apps
    "notifications",
    "mathfilters",
    "corsheaders",
    "simple_history",
    "django_filters",
    "widget_tweaks",
    "auditlog",
    "django_apscheduler",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_yasg",
    # Core EMPLINX apps
    "skylinx_auth",
    THEME_APP,
    "base",
    "employee",
    "recruitment",
    "leave",
    "pms",
    "onboarding",
    "asset",
    "attendance",
    "payroll",
    "accessibility",
    "skylinx_audit",
    "skylinx_widgets",
    "skylinx_crumbs",
    "skylinx_documents",
    "skylinx_views",
    "skylinx_automations",
    "skylinx_api",
    "biometric",
    "helpdesk",
    "offboarding",
    "skylinx_backup",
    "project",
    "skylinx_meet",
    "report",
    "whatsapp",
    "skylinx_ldap",
    "skylinx_dbtemplate",
    "subscriptions",
]

# ========================================
# REST FRAMEWORK CONFIGURATION
# ========================================

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "skylinx_api.auth.CompanyScopedJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter your Bearer token here",
        },
        "Basic": {"type": "basic", "description": "Basic authentication."},
    },
    "SECURITY": [{"Bearer": []}, {"Basic": []}],
}

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"

APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds

# ========================================
# MIDDLEWARE
# ========================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "skylinx.skylinx_middlewares.HtmxRedirectMiddleware",
    # EMPLINX-specific middlewares
    # licensing replaced by per-company subscriptions (SaaS multi-tenant)
    "subscriptions.middleware.SubscriptionMiddleware",
    "base.middleware.CompanyMiddleware",
    "base.middleware.ForcePasswordChangeMiddleware",
    "base.middleware.TwoFactorAuthMiddleware",
    "base.middleware.HTMXSecurityMiddleware",
    "accessibility.middlewares.AccessibilityMiddleware",
    "skylinx.skylinx_middlewares.MethodNotAllowedMiddleware",
    "skylinx.skylinx_middlewares.SVGSecurityMiddleware",
    "skylinx.skylinx_middlewares.MissingParameterMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "skylinx.urls"

# ========================================
# DATABASE CONFIGURATION
# ========================================
if env("DATABASE_URL", default=None):
    DATABASES = {"default": env.db()}
else:
    DATABASES = {
        "default": {
            "ENGINE": env("DB_ENGINE", default="django.db.backends.sqlite3"),
            "NAME": env("DB_NAME", default=os.path.join(BASE_DIR, "TestDB.sqlite3")),
            "USER": env("DB_USER", default=""),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default=""),
            "PORT": env("DB_PORT", default=""),
        }
    }

if DATABASES.get("default", {}).get("ENGINE") == "django.db.backends.sqlite3":
    # Critical SQLite optimizations for concurrency to prevent "database is locked"
    options = DATABASES["default"].setdefault("OPTIONS", {})
    options["timeout"] = 20
    options["transaction_mode"] = "IMMEDIATE"  # Django 5.1+ concurrency fix
    options["init_command"] = (
        "PRAGMA journal_mode=WAL;"
        "PRAGMA synchronous=NORMAL;"
        "PRAGMA mmap_size=134217728;"  # 128MB mmap
        "PRAGMA journal_size_limit=67108864;"
        "PRAGMA cache_size=-10000;"  # 10MB cache per connection
    )
else:
    # ponytail: persistent connections only for real DBs (Postgres/MySQL) — saves
    # a connect handshake per request. SQLite keeps fresh conns to avoid lock holds.
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# ========================================
# STATIC & MEDIA FILES
# ========================================
# ponytail: leading slash is required — without it, {% static %} URLs render
# relative and 404 on any page not served from "/" (e.g. /login/).
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Django 6 ignores STATICFILES_STORAGE — must use STORAGES. The old setting
# being a no-op is why prod had no compression and max-age=60 (default storage).
# Manifest storage = hashed names -> WhiteNoise serves 1yr immutable cache +
# precompressed .gz/.br. manifest_strict=False so a stray ref can't 500 a page.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "skylinx.storage.StaticStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")

# ========================================
# AUTHENTICATION & SECURITY
# ========================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "skylinx_auth.SkylinxUser"

# SAMEORIGIN (not DENY): the app frames its own pages/PDFs (e.g. the /terms/
# legal-document viewer). DENY blocks even same-origin framing -> "refused to
# connect". External sites are still blocked, so clickjacking protection holds.
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="SAMEORIGIN")

# ========================================
# TEMPLATES
# ========================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # EMPLINX dynamic context processors
                "skylinx.config.get_MENUS",
                "base.context_processors.get_companies",
                "base.context_processors.white_labelling_company",
                "base.context_processors.resignation_request_enabled",
                "base.context_processors.timerunner_enabled",
                "base.context_processors.intial_notice_period",
                "base.context_processors.check_candidate_self_tracking",
                "base.context_processors.check_candidate_self_tracking_rating",
                "base.context_processors.get_initial_prefix",
                "base.context_processors.biometric_app_exists",
                "base.context_processors.enable_late_come_early_out_tracking",
                "base.context_processors.enable_profile_edit",
                "skylinx_crumbs.context_processors.breadcrumbs",
                "subscriptions.context_processors.subscription_context",
            ],
            "loaders": [
                "skylinx_dbtemplate.loaders.Loader",
                (
                    "django.template.loaders.filesystem.Loader",
                    [BASE_DIR / THEME_APP / "templates"],
                ),
                "django.template.loaders.app_directories.Loader",
                ("django.template.loaders.filesystem.Loader", [BASE_DIR / "templates"]),
            ],
        },
    },
]

WSGI_APPLICATION = "skylinx.wsgi.application"

# ========================================
# INTERNATIONALIZATION
# ========================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

LANGUAGES = (
    ("en", "English (US)"),
    ("de", "Deutsche"),
    ("es", "Español"),
    ("fr", "Français"),
    ("ar", "عربى"),
    ("pt-br", "Português (Brasil)"),
    ("zh-hans", "Simplified Chinese"),
    ("zh-hant", "Traditional Chinese"),
    ("it", "Italian"),
    ("tr", "Turkish"),
)

LOCALE_PATHS = [join(BASE_DIR, "skylinx", "locale")]

# ========================================
# LOGGING, MESSAGES, OTHER GLOBALS
# ========================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_TAGS = {
    messages.DEBUG: "oh-alert--warning",
    messages.INFO: "oh-alert--info",
    messages.SUCCESS: "oh-alert--success",
    messages.WARNING: "oh-alert--warning",
    messages.ERROR: "oh-alert--danger",
}

LOGIN_URL = "/login"
SIMPLE_HISTORY_REVERT_DISABLED = True

DJANGO_NOTIFICATIONS_CONFIG = {
    "USE_JSONFIELD": True,
    "SOFT_DELETE": True,
    "USE_WATCHED": True,
    "NOTIFICATIONS_STORAGE": "notifications.storage.DatabaseStorage",
    "TEMPLATE": "notifications.html",
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "skylinx-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
            "CULL_FREQUENCY": 3,
        },
    }
}

# Default cache timeout in seconds (1 hour)
CACHE_TIMEOUT = 3600

# ========================================
# SKYLINX-SPECIFIC SETTINGS
# ========================================
WHITE_LABELLING = False
NESTED_SUBORDINATE_VISIBILITY = False
TWO_FACTORS_AUTHENTICATION = False

SIDEBARS = [
    # "recruitment",  # Hidden per product decision
    # "onboarding",  # Replaced by direct Add Employee flow
    "employee",
    "attendance",
    "leave",
    "payroll",
    "pms",
    "offboarding",
    "asset",
    "helpdesk",
    "project",
    "report",
]

# Audit logging is opt-in: the skylinx_audit app registers models explicitly
# through its registry, driven by AuditModelConfig and a default whitelist
# (Employee, EmployeeWorkInformation, EmployeeBankDetails).
AUDITLOG_INCLUDE_ALL_MODELS = False
AUDITLOG_EXCLUDE_TRACKING_MODELS = (
    # "<app_name>",
    # "<app_name>.<model>"
)

EMAIL_BACKEND = "base.backends.ConfiguredEmailBackend"

# Platform-default SMTP (gap #3). Used when a tenant has no DynamicEmailConfiguration
# of its own — the backend falls back to these. Read from .env (SMTP_* names).
EMAIL_HOST = env("SMTP_HOST", default="")
EMAIL_PORT = env.int("SMTP_PORT", default=587)
EMAIL_HOST_USER = env("SMTP_USER", default="")
EMAIL_HOST_PASSWORD = env("SMTP_PASS", default="")
# SMTP_SECURE=true => implicit SSL (port 465); false => STARTTLS (port 587, Gmail)
EMAIL_USE_SSL = env.bool("SMTP_SECURE", default=False)
EMAIL_USE_TLS = not EMAIL_USE_SSL
DEFAULT_FROM_EMAIL = env("SUPPORT_EMAIL", default=EMAIL_HOST_USER)
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default=EMAIL_HOST_USER)

"""
DB_INIT_PASSWORD: str

The password used for database setup and initialization. This password is a
48-character alphanumeric string generated using a UUID to ensure high entropy and security.
"""
DB_INIT_PASSWORD = env("DB_INIT_PASSWORD", default="")

# ========================================
# PERMISSIONS / CUSTOM LOGIC
# ========================================
NO_PERMISSION_MODALS = [
    "historicalbonuspoint",
    "assetreport",
    "assetdocuments",
    "returnimages",
    "holiday",
    "companyleave",
    "historicalavailableleave",
    "historicalleaverequest",
    "historicalleaveallocationrequest",
    "leaverequestconditionapproval",
    "historicalcompensatoryleaverequest",
    "employeepastleaverestrict",
    "overrideleaverequests",
    "historicalrotatingworktypeassign",
    "employeeshiftday",
    "historicalrotatingshiftassign",
    "historicalworktyperequest",
    "historicalshiftrequest",
    "multipleapprovalmanagers",
    "attachment",
    "announcementview",
    "emaillog",
    "driverviewed",
    "dashboardemployeecharts",
    "attendanceallowedip",
    "tracklatecomeearlyout",
    "historicalcontract",
    "overrideattendance",
    "overrideleaverequest",
    "overrideworkinfo",
    "multiplecondition",
    "historicalpayslip",
    "reimbursementmultipleattachment",
    "workrecord",
    "historicalticket",
    "skill",
    "historicalcandidate",
    "rejectreason",
    "historicalrejectedcandidate",
    "rejectedcandidate",
    "stagefiles",
    "stagenote",
    "questionordering",
    "recruitmentsurveyordering",
    "recruitmentsurveyanswer",
    "recruitmentgeneralsetting",
    "resume",
    "recruitmentmailtemplate",
    "profileeditfeature",
]

FILE_STORAGE = FileSystemStorage(location="csv_tmp/")

SKYLINX_DATE_FORMATS = {
    "DD/MM/YY": "%d/%m/%y",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MMMM D, YYYY": "%B %d, %Y",
    "DD MMMM, YYYY": "%d %B, %Y",
    "MMM. D, YYYY": "%b. %d, %Y",
    "D MMM. YYYY": "%d %b. %Y",
    "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
}

SKYLINX_TIME_FORMATS = {
    "hh:mm A": "%I:%M %p",  # 12-hour format
    "HH:mm": "%H:%M",  # 24-hour format
    "HH:mm:ss.SSSSSS": "%H:%M:%S.%f",  # 24-hour format with seconds and microseconds
}

BIO_DEVICE_THREADS = {}

DYNAMIC_URL_PATTERNS = []

APP_URLS = [
    "base.urls",
    "employee.urls",
]

APPS = [
    "auth",
    "base",
    "employee",
    "skylinx_documents",
    "skylinx_automations",
]

# ========================================
# LDAP CONFIGURATION (Default)
# ========================================
AUTH_LDAP_SERVER_URI = env("AUTH_LDAP_SERVER_URI", default="ldap://127.0.0.1:389")
AUTH_LDAP_BIND_DN = env("AUTH_LDAP_BIND_DN", default="cn=admin,dc=skylinx,dc=com")
AUTH_LDAP_BIND_PASSWORD = env("AUTH_LDAP_BIND_PASSWORD", default="")

AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

# Default LDAP settings
DEFAULT_LDAP_CONFIG = {
    "LDAP_SERVER": env("LDAP_SERVER", default="ldap://127.0.0.1:389"),
    "BIND_DN": env("BIND_DN", default="cn=admin,dc=skylinx,dc=com"),
    "BIND_PASSWORD": env("BIND_PASSWORD", default=""),
    "BASE_DN": env("BASE_DN", default="ou=users,dc=skylinx,dc=com"),
}

AUTHENTICATION_BACKENDS = [
    "base.auth_backends.IdentifierBackend",
    "django.contrib.auth.backends.ModelBackend",
    # "django_auth_ldap.backend.LDAPBackend",
]

AUTH_LDAP_ALWAYS_UPDATE_USER = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'skylinx_audit.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'base': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'skylinx': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
