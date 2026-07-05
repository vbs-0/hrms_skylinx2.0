"""AI action executor — the ONLY place the assistant can change data.

Security model (do not weaken):
- The LLM merely PROPOSES an action ({"action": ..., "id": ...}); nothing it
  says is trusted. Everything is re-validated here from the logged-in user's
  own role and company before anything happens.
- The action is executed by calling the SAME Django view a human clicks,
  through a RequestFactory request carrying the real user + session — so
  every permission decorator, hierarchy guard, balance deduction and
  notification runs identically to a manual click. No parallel business
  logic to drift out of sync.
- Only ever enabled when the company's ai_action_level is "execute" (itself
  clamped to the platform owner's ceiling).
"""
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from base.rbac import org_rank, HR_MANAGER_RANK

SUPPORTED_ACTIONS = ("approve_leave", "reject_leave")


def _clone_request(user, session, method="get", data=None):
    rf = RequestFactory()
    req = getattr(rf, method)("/", data or {}, HTTP_HX_REQUEST="true")
    req.user = user
    req.session = session
    req._messages = FallbackStorage(req)
    return req


def _messages_text(req):
    try:
        return " ".join(str(m) for m in req._messages)
    except Exception:
        return ""


def execute_action(request, action, params, company):
    """Validate and run one AI-proposed action. Returns {ok, message}."""
    from leave.models import LeaveRequest

    if org_rank(request.user) > HR_MANAGER_RANK:
        return {"ok": False, "message": "Your role can't perform this action."}
    if action not in SUPPORTED_ACTIONS:
        return {"ok": False, "message": f"'{action}' isn't an action I can perform."}
    try:
        req_id = int(params.get("id"))
    except (TypeError, ValueError):
        return {"ok": False, "message": "I couldn't identify which leave request you meant — mention its request ID."}

    lr = LeaveRequest.objects.filter(
        id=req_id, employee_id__employee_work_info__company_id=company
    ).first()
    if lr is None:
        return {"ok": False, "message": f"Leave request {req_id} doesn't exist in your company."}
    if lr.status != "requested":
        return {"ok": False, "message": f"Leave request {req_id} is already {lr.status} — nothing to do."}

    if action == "approve_leave":
        from leave.views import leave_request_approve

        fake = _clone_request(request.user, request.session, "get")
        leave_request_approve(fake, req_id)
        expected = "approved"
    else:
        from leave.views import leave_request_cancel

        reason = str(params.get("reason") or "Rejected via Emplinx Assistant on your instruction.")[:500]
        fake = _clone_request(request.user, request.session, "post", data={"reason": reason})
        leave_request_cancel(fake, req_id)
        expected = "rejected"

    lr.refresh_from_db()
    notes = _messages_text(fake)
    if lr.status == expected:
        emp = lr.employee_id
        return {
            "ok": True,
            "message": (
                f"Done — leave request {req_id} ({emp}, {lr.leave_type_id}, "
                f"{lr.start_date} to {lr.end_date}) is now {expected}."
            ),
        }
    return {
        "ok": False,
        "message": notes or f"Couldn't complete it — the request is still '{lr.status}'.",
    }
