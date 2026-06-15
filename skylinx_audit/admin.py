"""
admin.py
"""

from django.contrib import admin

from skylinx_audit.models import AuditTag, SkylinxAuditInfo, SkylinxAuditLog

# Register your models here.

admin.site.register(AuditTag)
