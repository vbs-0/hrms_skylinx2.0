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

from base.rbac import org_rank, CEO_RANK, HR_MANAGER_RANK


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

    def tok(self, value, kind="V"):
        # kind is a type label (NAME/DATE/MONEY/...) so the model knows what
        # the placeholder holds without seeing the real value.
        if value is None or value == "":
            return "-"
        self._n += 1
        placeholder = f"[[{kind}{self._n}]]"
        self.tokens[placeholder] = str(value)
        return placeholder

    def detokenize(self, text):
        for placeholder, real in self.tokens.items():
            text = text.replace(placeholder, real)
        # Anything left over is a placeholder the model invented (it sometimes
        # wraps a plain, already-real number/word in brackets on its own,
        # e.g. "[[ACTIVEEMPLOYEESCOUNT]]"). Deleting it outright silently
        # blanks out real words ("We have  active employees"), which reads as
        # broken. Un-wrap it instead — keep the inner text, drop the brackets
        # — so worst case is a slightly odd label, never a vanished value.
        return re.sub(r"\[\[([A-Za-z0-9_]+)\]\]", r"\1", text)


def _employee_context(user, tk=None):
    """Only the caller's OWN data. Real values are tokenized before this
    string ever leaves the server."""
    tk = tk or _Tokenizer()
    emp = getattr(user, "employee_get", None)
    if not emp:
        return "The user has no employee profile.", tk
    lines = [f"The user's name: {tk.tok(emp.get_full_name(), 'NAME')} (an employee)."]
    try:
        from leave.models import AvailableLeave

        for al in AvailableLeave.objects.filter(employee_id=emp)[:20]:
            lines.append(
                f"Leave type {tk.tok(al.leave_type_id, 'LEAVETYPE')}: {tk.tok(al.available_days, 'DAYS')} days available, "
                f"{tk.tok(al.carryforward_days, 'DAYS')} days carried forward."
            )
    except Exception:
        pass
    try:
        wi = emp.employee_work_info
        if wi:
            lines.append(
                f"Job role/position: {tk.tok(wi.job_position_id, 'ROLE')}; "
                f"Department: {tk.tok(wi.department_id, 'DEPT')}; Shift: {tk.tok(wi.shift_id, 'SHIFT')}; "
                f"Reporting manager: {tk.tok(wi.reporting_manager_id, 'NAME')}."
            )
    except Exception:
        pass
    try:
        from payroll.models.models import Payslip

        for p in Payslip.objects.filter(employee_id=emp).order_by("-start_date")[:3]:
            lines.append(
                f"Payslip {tk.tok(p.start_date, 'DATE')} to {tk.tok(p.end_date, 'DATE')}: gross {tk.tok(p.gross_pay, 'MONEY')}, "
                f"deduction {tk.tok(p.deduction, 'MONEY')}, net pay {tk.tok(p.net_pay, 'MONEY')}, status {tk.tok(p.status, 'STATUS')}."
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
                f"Attendance {tk.tok(a.attendance_date, 'DATE')}: in {tk.tok(a.attendance_clock_in or '-', 'TIME')}, "
                f"out {tk.tok(a.attendance_clock_out or '-', 'TIME')}, worked {tk.tok(a.attendance_worked_hour, 'HOURS')}."
            )
    except Exception:
        pass
    return "\n".join(lines), tk


def _company_context(user, role):
    """Aggregate, company-scoped stats for HR/CEO — no per-person PII dump.
    Counts are aggregate, not individually identifying, so left untokenized;
    the company name is tokenized since it's a real identifier."""
    tk = _Tokenizer()
    # HR/CEO are employees too — include their own data (name, leave,
    # attendance, payslips) so personal questions still work for them.
    own, tk = _employee_context(user, tk)
    lines = [f"The user is a {role.upper()}.", own]
    # current_company() wants a request; here we only have the user, so take
    # the company straight off their own employee record.
    company = None
    try:
        emp = getattr(user, "employee_get", None)
        if emp:
            company = emp.get_company()
    except Exception:
        pass
    if company:
        from employee.models import Employee
        from leave.models import LeaveRequest

        emp_qs = Employee.objects.filter(
            is_active=True, employee_work_info__company_id=company
        )
        lines.append(f"Company: {tk.tok(company.company, 'COMPANY')}.")
        lines.append(f"Active employees: {emp_qs.count()}.")
        level = getattr(company, "ai_action_level", "guidance")
        level_note = {
            "guidance": "You can only explain and guide — you cannot approve leave, generate payroll, or change any data.",
            "suggest": "You can suggest a specific action (e.g. approving a named leave request), but a human must click the real confirm button in Emplinx — you cannot execute it yourself.",
            "execute": "Direct execution isn't built yet even though this company's ceiling allows it — treat yourself as Suggest-only: propose the action, tell the user to confirm it in the UI.",
        }.get(level, "You can only explain and guide.")
        lines.append(f"Your action level for this company: {level}. {level_note}")
        try:
            pending = LeaveRequest.objects.filter(
                employee_id__employee_work_info__company_id=company,
                status="requested",
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

    # Verified navigation flows — written from the actual sidebar/templates.
    # The model MUST NOT invent UI steps beyond these; hallucinated buttons
    # ("click Generate Payslip") that don't exist destroy user trust.
    HOWTO_GUIDES = (
        "=== VERIFIED EMPLINX HOW-TO GUIDES (the ONLY navigation steps you may state) ===\n"
        "- Apply for leave: sidebar Leave > Apply Leave > Create button > pick "
        "leave type + dates > Save. Your manager then approves it under Leave > Leave Approval.\n"
        "- Approve/reject leave (managers/HR): sidebar Leave > Leave Approval > "
        "open the request > Approve or Reject.\n"
        "- Generate payslips (HR/admin): FIRST the employee must have an ACTIVE "
        "contract (Payroll > Pay Register > Create, set status Active). Then "
        "sidebar Payroll > Payslips > Actions button (top right) > Generate. "
        "Pick employees + period > confirm. There is NO standalone 'Generate "
        "Payslip' button — it is inside the Actions dropdown.\n"
        "- View own payslips: sidebar Payroll > Payslips (employees see their own).\n"
        "- Submit an expense/reimbursement: sidebar Payroll > Expenses > Create.\n"
        "- Form 16: sidebar Payroll > Form 16.\n"
        "- Check in/out (web): the Check In / Check Out button in the top navbar.\n"
        "- View attendance: sidebar Attendance > My Attendances (own) or "
        "Attendances (HR/managers, company-wide).\n"
        "- Fix a wrong attendance entry: sidebar Attendance > Attendance Requests > Create.\n"
        "- Request a shift change: sidebar Employee > Shift Requests > Create.\n"
        "- Add a new employee (HR/admin): sidebar Employee > Employees > Create "
        "button > fill personal info > then open the employee and complete Work "
        "Info (department, job position, shift, reporting manager, company).\n"
        "- View employee list: sidebar Employee > Employees.\n"
        "- Org chart: sidebar Employee > Organization Chart.\n"
        "- Raise a helpdesk ticket: sidebar Support > Tickets > Create.\n"
        "- FAQs: sidebar Support > FAQs.\n"
        "- Company settings (HR/admin): gear icon (top right) > Settings.\n"
        "- Update own profile: click your avatar (top right) > My Profile.\n"
        "=== END GUIDES ===\n"
    )

    system_prompt = (
        "You are Emplinx Assistant, a helper built into the Emplinx HR "
        "software.\n"
        "IN SCOPE (answer helpfully): the user's own HR data in CONTEXT "
        "(name, leave balance, shift, department, manager, payslips, "
        "attendance); anything about using Emplinx (how to apply for leave, "
        "request a shift change, view payslips, check in/out, raise a "
        "helpdesk ticket, update profile); and general workplace/HR "
        "questions (leave rules, working days, holidays, payroll concepts). "
        "'Can I apply for leave on Sunday?' or 'what is my name?' are IN "
        "scope — answer them.\n"
        "OUT OF SCOPE (politely refuse, suggest what you CAN do): topics "
        "with no HR/workplace connection — coding, math homework, trivia, "
        "essays, world news.\n"
        "WELLBEING: if the user expresses serious stress, burnout, "
        "hopelessness, or any hint of self-harm/wanting to disappear from "
        "work permanently, do NOT just answer the transactional question "
        "and move on. Acknowledge how they're feeling first, gently suggest "
        "they talk to their manager, HR, or a trusted person, and mention "
        "reaching out to a mental health helpline if it sounds serious — "
        "THEN address the HR question if relevant. Never be purely "
        "transactional in these cases.\n"
        "ACTIONS: CONTEXT may state your 'action level' for this company. "
        "NEVER claim you approved, rejected, generated, or changed anything "
        "— you cannot execute actions in this system yet, no matter what "
        "the action level says. If asked to do something like 'approve this "
        "leave' or 'generate payroll', tell them plainly you can't perform "
        "it yourself and point to the exact screen/button in Emplinx where "
        "a human does it.\n"
        "The CONTEXT below is the user's real, current data, but sensitive "
        "values are replaced with typed placeholder tokens like [[NAME1]], "
        "[[MONEY5]], [[DATE8]] for privacy — a separate system swaps them "
        "back to real values after you respond. The type prefix tells you "
        "what the token holds (NAME=a person's name, DEPT=department, "
        "MONEY=an amount, DATE/TIME/DAYS/HOURS/LEAVETYPE/SHIFT/STATUS "
        "likewise). When you use a value from CONTEXT, copy its token "
        "EXACTLY, character-for-character, double brackets included — never "
        "paraphrase, translate, reformat, or invent a token. Example: 'Your "
        "name is [[NAME1]].' or 'You have [[DAYS3]] days of [[LEAVETYPE2]] "
        "available.'\n"
        "IMPORTANT: only values already shown wrapped in [[...]] in CONTEXT "
        "need this treatment. Plain numbers/words in CONTEXT that are NOT "
        "wrapped (e.g. 'Active employees: 6.') are already final and safe to "
        "share — repeat them exactly as-is, as plain text. NEVER invent a "
        "new [[SOMENAME]] bracket around a plain value yourself — only copy "
        "brackets that were already there in CONTEXT.\n"
        "When CONTEXT answers the question, STATE THE ANSWER (using its "
        "tokens) directly. Do NOT tell the user to go check the UI when the "
        "answer is already in CONTEXT. Only give navigation/how-to steps if "
        "CONTEXT lacks the data needed to actually answer.\n"
        "REASON about what the data means for the user's specific question "
        "instead of defaulting to a generic how-to. Example: if they ask how "
        "to apply for leave but their available balance for every leave type "
        "in CONTEXT is 0, do NOT give the generic 'go to Leave section, pick "
        "dates, submit' steps — that's misleading since they have nothing to "
        "apply with. Instead say plainly they have 0 days available for "
        "[leave type], so a normal application will likely be rejected, and "
        "suggest the real options: check if a different leave type has "
        "balance, ask their reporting manager/HR about an exception or "
        "unpaid leave, or raise a helpdesk ticket. Never invent employee "
        "data; if CONTEXT truly has nothing on the topic, say so plainly. "
        "Be concise.\n"
        "NAVIGATION: when giving how-to steps, use ONLY the VERIFIED GUIDES "
        "below, word-for-word for menu names and button locations. NEVER "
        "invent a button, menu, or step that is not in the guides — a wrong "
        "click path is worse than no answer. If the task isn't covered by "
        "the guides, say you're not sure of the exact clicks and suggest "
        "the closest guide or raising a helpdesk ticket. Also mention any "
        "prerequisite listed in the guide (e.g. an active contract before "
        "payslip generation) BEFORE the steps. Never mention the guides "
        "themselves or that you were given a list — just answer naturally "
        "as if you know the product.\n\n"
        + HOWTO_GUIDES + "\n"
        "=== CONTEXT (real data, tokenized for privacy) ===\n" + ctx
    )
    try:
        raw_answer = _call_llm(cfg, system_prompt, history, user_msg)
    except Exception:
        return JsonResponse(
            {"error": "The assistant is temporarily unavailable. Try again shortly."},
            status=502,
        )
    # Server-side output guard: if a prompt-injection got the model to echo
    # its own instructions/context block, refuse instead of leaking them.
    if "=== CONTEXT" in raw_answer or "You are Emplinx Assistant, a helper" in raw_answer:
        return JsonResponse({
            "reply": "I can't share my internal instructions. Ask me about your "
                     "leave balance, shifts, payslips, attendance, or how to use Emplinx."
        })
    answer = tk.detokenize(raw_answer)
    return JsonResponse({"reply": answer})
