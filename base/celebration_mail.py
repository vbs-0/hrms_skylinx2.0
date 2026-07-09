"""
Shared sender for one-off "nice" HR emails that aren't tied to a specific
request (birthday wishes, welcome mail): styled like leave/threading.py's
LeaveMailSendThread but with no request/click-through link needed.
"""

import logging
import os
from email.mime.image import MIMEImage

from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from base.backends import ConfiguredEmailBackend

logger = logging.getLogger(__name__)


def send_celebration_mail(
    employee,
    subject,
    heading,
    message,
    emoji="🎉",
    template="base/mail_templates/celebration_template.html",
    extra_context=None,
    to_override=None,
    avatar_employee=None,
):
    """Send a styled celebration-style template. `employee` is used for the
    company/branding context; the actual recipient is `employee` unless
    `to_override` is given (used for birthday announcements sent to
    teammates, not the birthday person). `avatar_employee`, if given and it
    has a profile photo, is embedded inline as cid:avatar_photo so the
    template can show a real face instead of just an emoji.
    Best-effort: any failure is logged and swallowed so a bad recipient
    doesn't break a batch job (birthday sweep, welcome-on-hire) for everyone
    else."""
    to = to_override or employee.get_mail()
    if not to:
        return False

    try:
        company = employee.get_company()
        company_name = company.company if company else "EMPLINX"

        email_backend = ConfiguredEmailBackend()
        display_email_name = email_backend.dynamic_from_email_with_display_name

        context = {
            "heading": heading,
            "message": message,
            "emoji": emoji,
            "white_label_company_name": company_name,
        }
        avatar_path = None
        if avatar_employee and avatar_employee.employee_profile:
            try:
                if os.path.exists(avatar_employee.employee_profile.path):
                    avatar_path = avatar_employee.employee_profile.path
                    context["avatar_cid"] = "avatar_photo"
                    context["employee_name"] = avatar_employee.get_full_name()
            except (ValueError, NotImplementedError):
                pass
        if extra_context:
            context.update(extra_context)

        html_message = render_to_string(template, context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=html_message,
            from_email=display_email_name,
            to=[to],
            reply_to=[display_email_name],
        )
        email.attach_alternative(html_message, "text/html")

        if company and company.icon and os.path.exists(company.icon.path):
            image_path = company.icon.path
        else:
            image_path = finders.find("images/ui/skylinx-sticker-round.png")

        if image_path:
            with open(image_path, "rb") as f:
                logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<company_logo>")
                logo.add_header(
                    "Content-Disposition", "inline", filename=os.path.basename(image_path)
                )
                email.attach(logo)

        if avatar_path:
            with open(avatar_path, "rb") as f:
                photo = MIMEImage(f.read())
                photo.add_header("Content-ID", "<avatar_photo>")
                photo.add_header(
                    "Content-Disposition", "inline", filename=os.path.basename(avatar_path)
                )
                email.attach(photo)

        email.send()
        return True
    except Exception:
        logger.exception("celebration mail failed for %s", to)
        return False
