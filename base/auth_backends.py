"""
Login identifier flexibility.

By default a new employee's username is their email and password is their phone
(see employee.models.Employee.save). Clients expect to hand staff a simple
"username + phone" though, so accept the username, the personal email, the work
email, OR the phone number as the login identifier.
"""

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
import logging

from skylinx_auth.models import SkylinxUser

logger = logging.getLogger(__name__)


def _phone_key(value):
    return "".join(ch for ch in str(value or "").strip() if ch.isdigit())


class IdentifierBackend(ModelBackend):
    """Authenticate by username / email / work-email / phone, then password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        ident = username.strip()
        phone_ident = _phone_key(ident)
        user = (
            SkylinxUser.objects.filter(
                Q(username__iexact=ident)
                | Q(email__iexact=ident)
                | Q(employee_get__email__iexact=ident)
                | Q(employee_get__phone__iexact=ident)
                | Q(employee_get__phone=phone_ident)
                | Q(employee_get__employee_work_info__email__iexact=ident)
            )
            .distinct()
            .first()
        )
        logger.warning(
            "Auth backend lookup ident=%s user_id=%s employee_id=%s",
            ident,
            getattr(user, "id", None),
            getattr(getattr(user, "employee_get", None), "id", None) if user else None,
        )
        if user and self.user_can_authenticate(user):
            if user.check_password(password):
                logger.warning("Auth backend password match user_id=%s", user.id)
                return user
            employee = getattr(user, "employee_get", None)
            if employee:
                stored_phone = str(getattr(employee, "phone", "") or "").strip()
                normalized_phone = _phone_key(stored_phone)
                if password in {stored_phone, normalized_phone}:
                    logger.warning(
                        "Auth backend legacy phone match user_id=%s stored_phone=%s normalized_phone=%s",
                        user.id,
                        stored_phone,
                        normalized_phone,
                    )
                    return user
        logger.warning("Auth backend failed ident=%s", ident)
        return None
