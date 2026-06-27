"""
Transactional emails (welcome, etc.) — host-aware so links work on any
subdomain/cPanel domain without hardcoding a website.
"""

import logging
import threading

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def base_url():
    """Scheme+host from the current request, or a sane fallback from ALLOWED_HOSTS."""
    from skylinx.skylinx_middlewares import _thread_locals

    req = getattr(_thread_locals, "request", None)
    if req is not None:
        return f"{req.scheme}://{req.get_host()}"
    for h in getattr(settings, "ALLOWED_HOSTS", []):
        if h and h not in ("*", "localhost", "127.0.0.1"):
            return f"https://{h}"
    return ""


def _login_url():
    url = base_url()
    return f"{url}/login/" if url else "your HRMS login page"


def send_async(subject, body, to):
    """Fire-and-forget email to the given addresses (deduped, blanks dropped)."""
    seen = []
    for a in to:
        if a and a not in seen:
            seen.append(a)
    if not seen:
        return

    def _go():
        from base.backends import ConfiguredEmailBackend

        try:
            backend = ConfiguredEmailBackend()
            EmailMessage(
                subject, body, backend.dynamic_from_email_with_display_name, seen
            ).send(fail_silently=True)
        except Exception as exc:  # never break the request over an email
            logger.exception("send_async failed: %s", exc)

    threading.Thread(target=_go, daemon=True).start()


def send_company_welcome(company, admin_user, username):
    send_async(
        f"Welcome to EMPLINX — {company.company}",
        (
            f"Hi,\n\nYour company '{company.company}' is now set up on EMPLINX.\n\n"
            f"Sign in: {_login_url()}\n"
            f"Username: {username}\n\n"
            "Use the password you set to log in, then add your departments and team.\n\n"
            "— EMPLINX"
        ),
        [admin_user.email],
    )


def send_employee_welcome(employee):
    user = getattr(employee, "employee_user_id", None)
    if not user:
        return
    company = ""
    try:
        company = employee.employee_work_info.company_id.company
    except Exception:
        logger.warning("[email_utils] Failed to resolve company for welcome email", exc_info=True)
    send_async(
        f"Welcome to {company or 'the team'}",
        (
            f"Hi {employee.get_full_name()},\n\n"
            f"An account has been created for you{(' at ' + company) if company else ''}.\n\n"
            f"Sign in: {_login_url()}\n"
            f"Username: {user.username}\n"
            "Password: your phone number — please change it after your first login.\n\n"
            "— EMPLINX"
        ),
        [employee.email, getattr(getattr(employee, "employee_work_info", None), "email", None)],
    )
