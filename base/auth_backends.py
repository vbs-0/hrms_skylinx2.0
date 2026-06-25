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


class IdentifierBackend(ModelBackend):
    """Authenticate by username / email / work-email / phone, then password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        ident = username.strip()
        user = (
            SkylinxUser.objects.filter(
                Q(username__iexact=ident)
                | Q(email__iexact=ident)
                | Q(employee_get__email__iexact=ident)
                | Q(employee_get__phone=ident)
                | Q(employee_get__employee_work_info__email__iexact=ident)
            )
            .distinct()
            .first()
        )
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
