"""Role-scoped AI assistant.

Security model (do not weaken):
- The API key lives in AISettings and NEVER reaches the browser; this view
  proxies to the LLM server-side.
- What data the model is allowed to see is decided HERE from the logged-in
  user's own role + company — never from anything the client sends. An
  employee's request can only ever be built from that employee's own rows; an
  HR/CEO request is scoped to their company. Cross-tenant data is impossible
  because every queryset is filtered by the caller's company.
- We send the model a compact, pre-computed context (numbers, not raw PII
  dumps). Names/emails/salary of *other* people are never placed in the prompt.
"""
import json
import urllib.request

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from base.rbac import org_rank, current_company, CEO_RANK, HR_MANAGER_RANK


def _role_of(user):
    rank = org_rank(user)
    if rank <= CEO_RANK:
        return "ceo"
    if rank == HR_MANAGER_RANK:
        return "hr"
    return "employee"


def _employee_context(user):
    """Only the caller's OWN data."""
    emp = getattr(user, "employee_get", None)
    if not emp:
        return "The user has no employee profile."
    lines = [f"You are helping {emp.get_full_name()} (an employee)."]
    try:
        from leave.models import AvailableLeave

        for al in AvailableLeave.objects.filter(employee_id=emp)[:20]:
            lines.append(
                f"Leave '{al.leave_type_id}': {al.available_days} available, "
                f"{al.carryforward_days} carried forward."
            )
    except Exception:
        pass
    try:
        wi = emp.employee_work_info
        if wi:
            lines.append(
                f"Department: {wi.department_id}; Shift: {wi.shift_id}; "
                f"Reporting manager: {wi.reporting_manager_id}."
            )
    except Exception:
        pass
    return "\n".join(lines)


def _company_context(user, role):
    """Aggregate, company-scoped stats for HR/CEO — no per-person PII dump."""
    company = current_company(user)
    if not company:
        return "No company context available."
    from employee.models import Employee
    from leave.models import LeaveRequest

    emp_qs = Employee.objects.filter(
        is_active=True, employee_work_info__company_id=company
    )
    lines = [
        f"You are helping a {role.upper()} at {company.company}.",
        f"Active employees: {emp_qs.count()}.",
    ]
    try:
        pending = LeaveRequest.objects.filter(
            employee_id__employee_work_info__company_id=company, status="requested"
        ).count()
        lines.append(f"Pending leave requests: {pending}.")
    except Exception:
        pass
    return "\n".join(lines)


def _call_llm(cfg, system_prompt, user_msg):
    payload = json.dumps({
        "model": cfg.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }).encode()
    req = urllib.request.Request(
        cfg.api_base.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            # Cloudflare (fronting Groq/most providers) blocks urllib's
            # default "Python-urllib/x.y" UA as a bot signature — a real
            # browser-like UA is required or every request 403s.
            "User-Agent": "Mozilla/5.0 (compatible; Emplinx/1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


@login_required
@require_POST
def ai_chat(request):
    from subscriptions.models import AISettings

    cfg = AISettings.load()
    if not cfg.enabled or not cfg.api_key:
        return JsonResponse(
            {"error": "The AI assistant isn't enabled for your organization yet."},
            status=503,
        )

    role = _role_of(request.user)
    if role == "employee" and not cfg.allow_employee:
        return JsonResponse({"error": "AI assistant not available for your role."}, status=403)
    if role == "hr" and not cfg.allow_hr:
        return JsonResponse({"error": "AI assistant not available for your role."}, status=403)
    if role == "ceo" and not cfg.allow_ceo:
        return JsonResponse({"error": "AI assistant not available for your role."}, status=403)

    try:
        body = json.loads(request.body.decode())
    except Exception:
        return JsonResponse({"error": "Bad request."}, status=400)
    user_msg = (body.get("message") or "").strip()[:2000]
    if not user_msg:
        return JsonResponse({"error": "Empty message."}, status=400)

    if role == "employee":
        ctx = _employee_context(request.user)
    else:
        ctx = _company_context(request.user, role)

    system_prompt = (
        "You are Emplinx Assistant, an HR software helper. Answer only using "
        "the context below and general HR knowledge. Never invent employee "
        "data. If asked about someone the context doesn't cover, say you don't "
        "have access to that. Be concise.\n\n=== CONTEXT ===\n" + ctx
    )
    try:
        answer = _call_llm(cfg, system_prompt, user_msg)
    except Exception:
        return JsonResponse(
            {"error": "The assistant is temporarily unavailable. Try again shortly."},
            status=502,
        )
    return JsonResponse({"reply": answer})
