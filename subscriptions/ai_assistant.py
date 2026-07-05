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
- Sensitive values (name, department, manager, shift, payslip amounts,
  attendance times) are replaced with placeholder tokens like [[NAME]] before
  the request leaves our server. The LLM only ever sees placeholders; the
  real values live in a per-request dict and are substituted back into the
  reply here, after the LLM responds, before it reaches the browser. Any
  placeholder the model didn't echo back verbatim is stripped, not leaked.
"""
import json
import re
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


class _Tokenizer:
    """Swaps real values for [[TOKEN]] placeholders; reverses it on the reply."""

    def __init__(self):
        self.tokens = {}
        self._n = 0

    def tok(self, value):
        if value is None or value == "":
            return "-"
        self._n += 1
        placeholder = f"[[V{self._n}]]"
        self.tokens[placeholder] = str(value)
        return placeholder

    def detokenize(self, text):
        for placeholder, real in self.tokens.items():
            text = text.replace(placeholder, real)
        # Anything left over is a placeholder the model mangled/invented —
        # never let a raw [[...]] leak to the user.
        return re.sub(r"\[\[[A-Za-z0-9_]+\]\]", "", text)


def _employee_context(user):
    """Only the caller's OWN data. Real values are tokenized before this
    string ever leaves the server."""
    tk = _Tokenizer()
    emp = getattr(user, "employee_get", None)
    if not emp:
        return "The user has no employee profile.", tk
    lines = [f"You are helping {tk.tok(emp.get_full_name())} (an employee)."]
    try:
        from leave.models import AvailableLeave

        for al in AvailableLeave.objects.filter(employee_id=emp)[:20]:
            lines.append(
                f"Leave '{tk.tok(al.leave_type_id)}': {tk.tok(al.available_days)} available, "
                f"{tk.tok(al.carryforward_days)} carried forward."
            )
    except Exception:
        pass
    try:
        wi = emp.employee_work_info
        if wi:
            lines.append(
                f"Department: {tk.tok(wi.department_id)}; Shift: {tk.tok(wi.shift_id)}; "
                f"Reporting manager: {tk.tok(wi.reporting_manager_id)}."
            )
    except Exception:
        pass
    try:
        from payroll.models.models import Payslip

        for p in Payslip.objects.filter(employee_id=emp).order_by("-start_date")[:3]:
            lines.append(
                f"Payslip {tk.tok(p.start_date)} to {tk.tok(p.end_date)}: gross {tk.tok(p.gross_pay)}, "
                f"deduction {tk.tok(p.deduction)}, net pay {tk.tok(p.net_pay)}, status {tk.tok(p.status)}."
            )
    except Exception:
        pass
    try:
        from datetime import timedelta

        from django.utils import timezone

        from attendance.models import Attendance

        since = timezone.localdate() - timedelta(days=14)
        for a in Attendance.objects.filter(
            employee_id=emp, attendance_date__gte=since
        ).order_by("-attendance_date")[:10]:
            lines.append(
                f"Attendance {tk.tok(a.attendance_date)}: in {tk.tok(a.attendance_clock_in or '-')}, "
                f"out {tk.tok(a.attendance_clock_out or '-')}, worked {tk.tok(a.attendance_worked_hour)}."
            )
    except Exception:
        pass
    return "\n".join(lines), tk


def _company_context(user, role):
    """Aggregate, company-scoped stats for HR/CEO — no per-person PII dump.
    Counts are aggregate, not individually identifying, so left untokenized;
    the company name is tokenized since it's a real identifier."""
    tk = _Tokenizer()
    company = current_company(user)
    if not company:
        return "No company context available.", tk
    from employee.models import Employee
    from leave.models import LeaveRequest

    emp_qs = Employee.objects.filter(
        is_active=True, employee_work_info__company_id=company
    )
    lines = [
        f"You are helping a {role.upper()} at {tk.tok(company.company)}.",
        f"Active employees: {emp_qs.count()}.",
    ]
    try:
        pending = LeaveRequest.objects.filter(
            employee_id__employee_work_info__company_id=company, status="requested"
        ).count()
        lines.append(f"Pending leave requests: {pending}.")
    except Exception:
        pass
    return "\n".join(lines), tk


def _call_llm(cfg, system_prompt, history, user_msg):
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})
    payload = json.dumps({
        "model": cfg.model_name,
        "messages": messages,
        "temperature": 0.2,
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

    # Client-side conversation memory: only ever echoed back what THIS
    # session already sent/received in THIS request's own payload — never
    # stored server-side, never shared across users. Cap to last 6 turns
    # (12 messages) and clamp each message length so a malicious client
    # can't blow up the token bill or smuggle a huge prompt-injection blob.
    raw_history = body.get("history") or []
    history = []
    if isinstance(raw_history, list):
        for turn in raw_history[-12:]:
            if not isinstance(turn, dict):
                continue
            r = turn.get("role")
            c = str(turn.get("content", ""))[:1000]
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    if role == "employee":
        ctx, tk = _employee_context(request.user)
    else:
        ctx, tk = _company_context(request.user, role)

    system_prompt = (
        "You are Emplinx Assistant, a helper built into the Emplinx HR "
        "software. You ONLY answer questions about: the user's own HR data "
        "(leave balance, shifts, payslips, attendance) using the context "
        "below, and how to use Emplinx features. "
        "The CONTEXT below already contains the user's real, current data, "
        "but names/numbers/dates are replaced with placeholder tokens like "
        "[[V3]] for privacy — a separate system swaps them back to real "
        "values after you respond. When you use a value from CONTEXT, copy "
        "its [[V_]] token EXACTLY, character-for-character, brackets "
        "included — never paraphrase, translate, reformat, or invent a "
        "token. "
        "When CONTEXT answers the question, STATE THE ANSWER (using its "
        "tokens) directly. Do NOT tell the user to go log in and check the "
        "UI themselves when the answer is already in CONTEXT — that is a "
        "useless non-answer. Only give navigation guidance ('go to the Leave "
        "section') if CONTEXT does NOT contain the data needed to answer. "
        "You must REFUSE anything else — general knowledge, coding help, "
        "math, trivia, writing essays, or any topic unrelated to HR/Emplinx — "
        "even if asked directly. When refusing, say briefly that you only "
        "handle Emplinx/HR questions and suggest what you *can* help with. "
        "Never invent employee data; if CONTEXT truly has nothing on the "
        "topic, say so plainly. Be concise.\n\n"
        "=== CONTEXT (real data, tokenized for privacy) ===\n" + ctx
    )
    try:
        raw_answer = _call_llm(cfg, system_prompt, history, user_msg)
    except Exception:
        return JsonResponse(
            {"error": "The assistant is temporarily unavailable. Try again shortly."},
            status=502,
        )
    answer = tk.detokenize(raw_answer)
    return JsonResponse({"reply": answer})
