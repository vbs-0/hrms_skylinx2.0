"""
Login identifier flexibility.

By default a new employee's username is their email and password is their phone
(see employee.models.Employee.save). Username-based login is intentionally NOT
accepted here (client requirement) - only the personal email, work email, or
phone number are valid login identifiers.
"""

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
import logging

from skylinx_auth.models import SkylinxUser

logger = logging.getLogger(__name__)


def _phone_key(value):
    return "".join(ch for ch in str(value or "").strip() if ch.isdigit())


def _dedupe_users(querysets):
    seen = set()
    users = []
    for queryset in querysets:
        for user in queryset:
            if user.pk in seen:
                continue
            seen.add(user.pk)
            users.append(user)
    return users


class IdentifierBackend(ModelBackend):
    """Authenticate by email / work-email / phone (NOT username), then password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        ident = username.strip()
        phone_ident = _phone_key(ident)
        querysets = [
            SkylinxUser.objects.filter(email__iexact=ident),
            SkylinxUser.objects.filter(employee_get__employee_work_info__email__iexact=ident),
            SkylinxUser.objects.filter(employee_get__email__iexact=ident),
        ]
        # phone_ident is '' for a non-numeric ident (e.g. an email/username) -
        # matching on an empty string would false-match every blank-phone employee.
        if phone_ident:
            querysets.append(
                SkylinxUser.objects.filter(
                    Q(employee_get__phone__iexact=ident)
                    | Q(employee_get__phone=phone_ident)
                )
            )
        users = _dedupe_users(querysets)
        logger.warning(
            "Auth backend lookup ident=%s candidate_count=%s",
            ident,
            len(users),
        )
        for user in users:
            if not self.user_can_authenticate(user):
                continue
            # Only the hashed password counts. New employees get their phone
            # SET as the initial password (hashed), so first-login-with-phone
            # still works via check_password — but once they change it, the
            # phone must never again act as a plain-text master key.
            if user.check_password(password):
                return user
        logger.warning("Auth backend failed ident=%s", ident)
        return None
