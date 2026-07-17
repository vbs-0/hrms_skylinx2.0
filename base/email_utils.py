"""
Transactional emails (welcome, etc.) — host-aware so links work on any
subdomain/cPanel domain without hardcoding a website.
"""

import logging
import os
import threading
from email.mime.image import MIMEImage

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _render_branded(heading, body_html, cta_url=None, cta_label="", cta_note=""):
    """Render the branded onboarding email shell to an HTML string."""
    return render_to_string(
        "base/mail_templates/onboarding_email.html",
        {
            "heading": heading,
            "body_html": body_html,
            "cta_url": cta_url,
            "cta_label": cta_label,
            "cta_note": cta_note,
        },
    )


def _attach_logo(msg):
    """Embed the Emplinx logo inline as cid:company_logo (best-effort).
    Uses skylinx-logo-email.png — the same logo pre-flattened onto the solid
    header purple (#6b58b5), NOT the transparent app asset. Email clients
    (Gmail especially) are unreliable about honoring real PNG alpha in inline
    images and will matte transparent areas (like the hole in a capital P)
    to white — baking the background in at asset-build time sidesteps that
    entirely instead of fighting each client's renderer."""
    path = finders.find("images/ui/skylinx-logo-email.png") or finders.find(
        "images/ui/skylinx-logo.png"
    )
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            logo = MIMEImage(f.read())
        logo.add_header("Content-ID", "<company_logo>")
        logo.add_header("Content-Disposition", "inline", filename="emplinx-logo.png")
        msg.attach(logo)


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


def send_from_intake(subject, to, heading, body_html, cta_url=None,
                     cta_label="", cta_note="", text_fallback=""):
    """Fire-and-forget BRANDED email from the dedicated client-intake mailbox
    (DynamicEmailConfiguration with purpose='client_intake'). Renders the
    Emplinx-branded HTML shell with the logo embedded inline. Falls back to
    the normal mail resolution if no intake config exists yet."""
    seen = [a for a in dict.fromkeys(to) if a]
    if not seen:
        return

    def _go():
        from skylinx.skylinx_middlewares import _thread_locals
        from base.backends import ConfiguredEmailBackend

        try:
            _thread_locals.email_purpose = "client_intake"
            backend = ConfiguredEmailBackend()
            html = _render_branded(heading, body_html, cta_url, cta_label, cta_note)
            msg = EmailMultiAlternatives(
                subject,
                text_fallback or heading,
                backend.dynamic_from_email_with_display_name,
                seen,
            )
            msg.attach_alternative(html, "text/html")
            _attach_logo(msg)
            msg.send(fail_silently=True)
        except Exception as exc:
            logger.exception("send_from_intake failed: %s", exc)
        finally:
            _thread_locals.email_purpose = None

    threading.Thread(target=_go, daemon=True).start()


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
