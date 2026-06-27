"""
Login identifier flexibility.

By default a new employee's username is their email and password is their phone
(see employee.models.Employee.save). Clients expect to hand staff a simple
"username + phone" though, so accept the username, the personal email, the work
email, OR the phone number as the login identifier.
"""

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from skylinx_auth.models import SkylinxUser


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
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
