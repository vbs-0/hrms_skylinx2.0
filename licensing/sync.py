"""
Client -> vendor license sync.

Calls the vendor license server to refresh entitlements for the stored key and
writes them into the LicenseConfig singleton. The server is the source of
truth, so an expired/revoked/upgraded license is reflected on the next sync.

Server contract (implement on the vendor `server` instance):
    POST {LICENSE_SERVER_URL}/api/license/verify   body: {"key": "..."}
    200 -> {"valid": bool, "plan_name": str, "employee_limit": int|null,
            "features": [str], "expires_on": "YYYY-MM-DD"|null, "status": str}

ponytail: stdlib urllib, no new dependency. Swap in signature verification of
the response here when the crypto layer lands — single chokepoint.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

from .models import LicenseConfig


def sync_license(timeout=10):
    """Return (ok: bool, message: str)."""
    cfg = LicenseConfig.get()
    if not cfg.license_key:
        return False, "No license key set."

    server = getattr(settings, "LICENSE_SERVER_URL", "")
    if not server:
        return False, "LICENSE_SERVER_URL is not configured."

    url = server.rstrip("/") + "/api/license/verify"
    data = json.dumps({"key": cfg.license_key}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return False, f"Could not reach license server: {e.reason}"
    except (ValueError, TimeoutError) as e:
        return False, f"Invalid response from license server: {e}"

    if not payload.get("valid"):
        cfg.status = payload.get("status", "invalid")
        cfg.enabled_features = []
        cfg.last_synced = timezone.now()
        cfg.save()
        return False, "License is not valid (expired or revoked)."

    cfg.plan_name = payload.get("plan_name", "")
    cfg.employee_limit = payload.get("employee_limit")
    cfg.enabled_features = payload.get("features", [])
    cfg.expires_on = payload.get("expires_on") or None
    cfg.status = payload.get("status", "active")
    cfg.last_synced = timezone.now()
    cfg.save()
    return True, f"Synced. Plan: {cfg.plan_name or 'n/a'}."
