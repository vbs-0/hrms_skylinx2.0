"""skylinx URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path, re_path
from django.views.i18n import JavaScriptCatalog

import notifications.urls

from . import settings


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


def privacy_policy(request):
    return HttpResponse(PRIVACY_POLICY_HTML)


PRIVACY_POLICY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Privacy Policy - Emplinx HRMS</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Arial,Helvetica,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.6;color:#222}
h1{font-size:26px}h2{font-size:19px;margin-top:32px}
</style>
</head>
<body>
<h1>Privacy Policy - Emplinx HRMS</h1>
<p>Last updated: July 1, 2026</p>

<p>Emplinx HRMS ("the App") is a workforce management application provided by
Skylinx Global Solutions for use by our client organizations and their
employees. This policy explains what data the App collects and how it is
used.</p>

<h2>Information We Collect</h2>
<ul>
<li><strong>Name, email address, and phone number</strong> - used to identify
your employee account and for login.</li>
<li><strong>Precise location</strong> - collected during attendance
check-in/check-out to verify you are at an authorized work location.</li>
<li><strong>Photos (selfies)</strong> - captured during attendance check-in
for identity verification.</li>
</ul>

<h2>How We Use This Information</h2>
<p>Data collected is used solely to operate core HR functions: attendance
tracking, payroll processing, and employee directory features within your
employer's Emplinx HRMS account. We do not sell or share your personal data
with third parties or advertisers.</p>

<h2>Data Storage and Security</h2>
<p>All data is transmitted over encrypted HTTPS connections and stored on
servers operated by Skylinx Global Solutions. Access is restricted to your
employer's authorized HR administrators.</p>

<h2>Data Retention and Deletion</h2>
<p>Data is retained for as long as your employer's account remains active.
Employees may request deletion of their personal data by contacting their HR
administrator or emailing us directly.</p>

<h2>Children's Privacy</h2>
<p>This App is intended for use by employees of client organizations and is
not directed at children under 13.</p>

<h2>Contact Us</h2>
<p>Questions about this policy can be sent to
<a href="mailto:skylinxcode@gmail.com">skylinxcode@gmail.com</a>.</p>
</body>
</html>"""


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("base.urls")),
    path("", include("company_profile.urls")),
    path("", include("skylinx_automations.urls")),
    path("", include("skylinx_views.urls")),
    path("", include("skylinx_audit.urls")),
    path("employee/", include("employee.urls")),
    path("api/", include("skylinx_api.urls")),
    path("manage/", include("subscriptions.urls")),
    path("buzz/", include("buzz.urls")),
    path("konnect/", include("konnect.urls")),
    path("subscription/", include("subscriptions.client_urls")),
    path("skylinx-widget/", include("skylinx_widgets.urls")),
    re_path(
        "^inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("health/", health_check),
    path("privacy/", privacy_policy),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Register dynamically generated tab URLs for SkylinxProfileView subclasses at startup
from skylinx_views.generic.cbv.views import SkylinxProfileView
for cls in list(SkylinxProfileView._registry):
    cls.register_tab_urls()
