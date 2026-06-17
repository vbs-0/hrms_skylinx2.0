"""
Vendor license-verify API (server role).

This is the endpoint client instances hit on sync:
    POST /api/license/verify   body: {"key": "..."}

Returns the license's current entitlements. The vendor server is the source of
truth, so revoking/expiring/upgrading a License here propagates to the client
on its next sync. Public endpoint (no auth) — the key itself is the credential.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def verify(request):
    try:
        body = json.loads(request.body.decode() or "{}")
    except ValueError:
        return JsonResponse({"valid": False, "status": "bad_request"}, status=400)

    key = (body.get("key") or "").strip()
    if not key:
        return JsonResponse({"valid": False, "status": "no_key"}, status=400)

    from .models import License

    lic = License.objects.filter(key=key).select_related("plan").first()
    if not lic:
        return JsonResponse({"valid": False, "status": "not_found"})

    # Auto-flip a lapsed license so tracking/UI stay accurate.
    if lic.status == "active" and lic.is_expired:
        lic.status = "expired"
        lic.save(update_fields=["status"])

    if not lic.is_valid():
        return JsonResponse({"valid": False, "status": lic.status})

    return JsonResponse(
        {
            "valid": True,
            "status": "active",
            "plan_name": lic.plan.name if lic.plan else "",
            "employee_limit": lic.employee_limit,
            "features": list(lic.features or []),
            "expires_on": lic.expires_on.isoformat() if lic.expires_on else None,
        }
    )
