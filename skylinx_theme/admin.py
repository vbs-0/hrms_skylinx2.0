"""
Admin registration for the skylinx_theme app
"""

from django.contrib import admin

from skylinx_theme.models import CompanyTheme, SkylinxColorTheme

# Register your skylinx_theme models here.
admin.site.register(SkylinxColorTheme)
admin.site.register(CompanyTheme)
