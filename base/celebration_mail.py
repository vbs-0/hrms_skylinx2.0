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


def send_celebration_mail(employee, subject, heading, message, emoji="🎉"):
    """Send the styled celebration template to `employee`. Best-effort: any
    failure is logged and swallowed so a bad recipient doesn't break a batch
    job (birthday sweep, welcome-on-hire) for everyone else."""
    to = employee.get_mail()
    if not to:
        return False

    try:
        company = employee.get_company()
        company_name = company.company if company else "EMPLINX"

        email_backend = ConfiguredEmailBackend()
        display_email_name = email_backend.dynamic_from_email_with_display_name

        html_message = render_to_string(
            "base/mail_templates/celebration_template.html",
            {
                "heading": heading,
                "message": message,
                "emoji": emoji,
                "white_label_company_name": company_name,
            },
        )

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

        email.send()
        return True
    except Exception:
        logger.exception("celebration mail failed for %s", to)
        return False
