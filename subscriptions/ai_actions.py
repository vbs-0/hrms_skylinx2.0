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
- The set of employees/records an action touches is ALWAYS rebuilt here from
  the caller's own company — never from IDs the model made up.
"""
import datetime

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from base.rbac import org_rank, HR_MANAGER_RANK

SUPPORTED_ACTIONS = ("approve_leave", "reject_leave", "create_leave", "generate_payroll")


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
    if org_rank(request.user) > HR_MANAGER_RANK:
        return {"ok": False, "message": "Your role can't perform this action."}
    if action in ("approve_leave", "reject_leave"):
        return _do_leave(request, action, params, company)
    if action == "create_leave":
        return _do_create_leave(request, params, company)
    if action == "generate_payroll":
        return _do_generate_payroll(request, params, company)
    return {"ok": False, "message": f"'{action}' isn't an action I can perform."}


def describe_action(action, params, company):
    """Plain-English, real-data (untokenized) summary of a proposed action,
    for the Proceed/Cancel confirmation card. Returns None if the action/
    params don't even validate enough to describe (caller treats that as a
    hard failure — never shows a confirm card for garbage input)."""
    if action not in SUPPORTED_ACTIONS:
        return None
    try:
        if action in ("approve_leave", "reject_leave"):
            from leave.models import LeaveRequest

            req_id = int(params.get("id"))
            lr = LeaveRequest.objects.filter(
                id=req_id, employee_id__employee_work_info__company_id=company
            ).first()
            if lr is None or lr.status != "requested":
                return None
            verb = "Approve" if action == "approve_leave" else "Reject"
            extra = f" Reason: {params.get('reason')}." if action == "reject_leave" and params.get("reason") else ""
            return (
                f"{verb} leave request #{req_id} — {lr.employee_id}, "
                f"{lr.leave_type_id}, {lr.start_date} to {lr.end_date} "
                f"({lr.requested_days} day(s)).{extra}"
            )
        if action == "create_leave":
            from employee.models import Employee
            from leave.models import LeaveType

            emp = Employee.objects.filter(
                id=params.get("employee_id"), employee_work_info__company_id=company
            ).first()
            leave_type = LeaveType.objects.filter(
                id=params.get("leave_type_id"), company_id=company
            ).first()
            if emp is None or leave_type is None:
                return None
            reason = params.get("reason") or "-"
            return (
                f"Create and assign a {leave_type} leave request for {emp}: "
                f"{params.get('start_date')} to {params.get('end_date')}. Reason: {reason}."
            )
        if action == "generate_payroll":
            start, end = _period(params)
            return f"Generate draft payslips for all eligible employees, period {start} to {end}."
    except Exception:
        return None
    return None


def _do_leave(request, action, params, company):
    from leave.models import LeaveRequest

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


def _do_create_leave(request, params, company):
    """Create+assign a leave request for a named employee. Mirrors the same
    balance/overlap checks as the mobile apply endpoint
    (skylinx_api/api_views/leave/mobile_views.py) and lands in "requested"
    status — same as a normal application; still needs a separate
    approve_leave action/click, this only files it."""
    import datetime as _dt

    from employee.models import Employee
    from leave.methods import calculate_requested_days
    from leave.models import AvailableLeave, LeaveRequest, LeaveType

    emp = Employee.objects.filter(
        id=params.get("employee_id"), employee_work_info__company_id=company
    ).first()
    if emp is None:
        return {"ok": False, "message": "That employee isn't in your company — nothing was created."}

    leave_type = LeaveType.objects.filter(
        id=params.get("leave_type_id"), company_id=company
    ).first()
    if leave_type is None:
        return {"ok": False, "message": "That leave type doesn't exist for your company — nothing was created."}

    try:
        start_date = _dt.datetime.strptime(str(params.get("start_date")), "%Y-%m-%d").date()
        end_date = _dt.datetime.strptime(str(params.get("end_date")), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return {"ok": False, "message": "Invalid dates — use YYYY-MM-DD. Nothing was created."}
    if start_date > end_date:
        return {"ok": False, "message": "Start date is after end date — nothing was created."}

    available = AvailableLeave.objects.filter(employee_id=emp, leave_type_id=leave_type).first()
    if available is None:
        return {"ok": False, "message": f"{leave_type} isn't assigned to {emp} — nothing was created."}

    overlapping = LeaveRequest.objects.filter(
        employee_id=emp, start_date__lte=end_date, end_date__gte=start_date
    ).exclude(status__in=["cancelled", "rejected"])
    if overlapping.exists():
        return {"ok": False, "message": f"{emp} already has a leave request overlapping those dates — nothing was created."}

    requested_days = calculate_requested_days(start_date, end_date, "full_day", "full_day")
    total_available = (available.available_days or 0) + (available.carryforward_days or 0)
    if requested_days > total_available:
        return {
            "ok": False,
            "message": f"{emp} only has {total_available} day(s) of {leave_type} available, but {requested_days} were requested — nothing was created.",
        }

    reason = str(params.get("reason") or "Created via Emplinx Assistant.")[:500]
    lr = LeaveRequest.objects.create(
        employee_id=emp,
        leave_type_id=leave_type,
        start_date=start_date,
        start_date_breakdown="full_day",
        end_date=end_date,
        end_date_breakdown="full_day",
        description=reason,
        status="requested",
        created_by=request.user.employee_get if hasattr(request.user, "employee_get") else None,
        requested_days=requested_days,
    )
    try:
        from leave.threading import LeaveMailSendThread

        LeaveMailSendThread(request, lr, type="request").start()
    except Exception:
        pass
    return {
        "ok": True,
        "message": (
            f"Created leave request #{lr.id} for {emp}: {leave_type}, {start_date} "
            f"to {end_date} ({requested_days} day(s)). It's in 'requested' status — "
            "approve it separately when ready."
        ),
    }


def _period(params):
    """Payroll period. Optional params['month']='YYYY-MM'; default = the
    current month, 1st to today (matches the UI's own pre-filled range).
    Never returns a future end date."""
    today = datetime.date.today()
    month = params.get("month")
    if month:
        try:
            y, m = (int(x) for x in str(month).split("-")[:2])
            start = datetime.date(y, m, 1)
            nxt = datetime.date(y + 1, 1, 1) if m == 12 else datetime.date(y, m + 1, 1)
            end = min(nxt - datetime.timedelta(days=1), today)
            return start, end
        except Exception:
            pass
    return today.replace(day=1), today


def _do_generate_payroll(request, params, company):
    from payroll.models.models import Contract, Payslip
    from payroll.views.component_views import generate_payslip

    start, end = _period(params)

    # Eligible employees are rebuilt HERE from the caller's own company — the
    # model never chooses who gets paid. Only active-contract employees.
    eligible_ids = list(
        Contract.objects.filter(
            contract_status="active",
            employee_id__is_active=True,
            employee_id__employee_work_info__company_id=company,
        )
        .values_list("employee_id", flat=True)
        .distinct()
    )
    if not eligible_ids:
        return {
            "ok": False,
            "message": (
                "No employees have their CTC set yet, so there's nothing to run "
                "payroll for. Set CTC under Employee → [employee] → Work Info, "
                "then activate their pay-register entry under Payroll → Pay "
                "Register, then ask me again."
            ),
        }

    before = Payslip.objects.filter(
        employee_id__employee_work_info__company_id=company,
        start_date=start,
        end_date=end,
    ).count()

    fake = _clone_request(
        request.user,
        request.session,
        "post",
        data={
            "employee_id": [str(i) for i in eligible_ids],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    try:
        generate_payslip(fake)
    except Exception:
        return {
            "ok": False,
            "message": "Payroll generation hit an error — please run it manually under Payroll → Payslips → Actions → Generate.",
        }

    after = Payslip.objects.filter(
        employee_id__employee_work_info__company_id=company,
        start_date=start,
        end_date=end,
    ).count()
    created = after - before
    notes = _messages_text(fake)
    if created > 0:
        return {
            "ok": True,
            "message": (
                f"Generated {created} draft payslip(s) for the period {start} to "
                f"{end}. Review and confirm them under Payroll → Payslips."
                + (f" Note: {notes}" if notes else "")
            ),
        }
    return {
        "ok": False,
        "message": notes or "No payslips were generated — check that eligible contracts have a wage set for this period.",
    }
