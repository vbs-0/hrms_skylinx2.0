"""
Provision a client (Company) for go-live:

  * creates the three default, per-tenant user groups
    (HR Manager / HR / Employee) with a sensible starter permission set, and
  * optionally creates a company-scoped admin LOGIN (a non-superuser, so the
    tenant-isolation middleware hard-locks them to this company).

Idempotent: re-running only fills gaps, never duplicates.

    python manage.py setup_client --company "Acme"
    python manage.py setup_client --company 5 \
        --admin-username acme_admin --admin-password 'S3cret!' \
        --admin-email admin@acme.com

ponytail: the permission sets below are a STARTER baseline by app-label, not a
hand-tuned matrix. Refine per client in Settings > User Groups after go-live.
"""

import uuid

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import Company, CompanyGroup
from base.rbac import scoped_name
from employee.models import Employee, EmployeeWorkInformation
from skylinx_auth.models import SkylinxUser

# HR suite an HR role legitimately touches. Genuinely global apps (auth, admin,
# sessions, subscriptions, licensing, skylinx_* infra) are deliberately excluded.
HR_APPS = [
    "employee", "leave", "attendance", "payroll", "recruitment", "pms",
    "onboarding", "offboarding", "asset", "helpdesk", "project",
    "geofencing", "base",
]
# What an ordinary employee can self-serve (view + apply for own leave).
EMPLOYEE_VIEW_APPS = ["employee", "leave", "attendance", "payroll", "asset", "helpdesk"]


def perms(app_labels, actions=None):
    """Permissions in the given apps, optionally limited to add/change/delete/view."""
    from django.db.models import Q

    qs = Permission.objects.filter(content_type__app_label__in=app_labels)
    if actions:
        cond = Q()
        for a in actions:
            cond |= Q(codename__startswith=f"{a}_")
        qs = qs.filter(cond)
    return qs


# role -> (app_labels, actions or None=all)
ROLE_PERMS = {
    "HR Manager": (HR_APPS, None),                       # full HR suite
    "HR": (HR_APPS, ["add", "change", "view"]),          # no deletes
    "Employee": (EMPLOYEE_VIEW_APPS, ["view"]),          # self-service read
}


class Command(BaseCommand):
    help = "Provision default groups (and optionally a scoped admin) for a client company."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True,
                            help="Company id or exact name to provision.")
        parser.add_argument("--admin-username")
        parser.add_argument("--admin-password")
        parser.add_argument("--admin-email", default="")
        parser.add_argument("--admin-first-name", default="Client")
        parser.add_argument("--admin-last-name", default="Admin")

    def get_company(self, ref):
        company = None
        if str(ref).isdigit():
            company = Company.objects.filter(id=int(ref)).first()
        if not company:
            company = Company.objects.filter(company=ref).first()
        if not company:
            raise CommandError(f'No company matching "{ref}".')
        return company

    @transaction.atomic
    def handle(self, *args, **opts):
        company = self.get_company(opts["company"])
        self.stdout.write(f"Provisioning: {company} (id={company.id})")

        groups = {}
        for label, (apps, actions) in ROLE_PERMS.items():
            name = scoped_name(company.id, label)
            group, created = Group.objects.get_or_create(name=name)
            CompanyGroup.objects.get_or_create(
                group=group, defaults={"company": company}
            )
            group.permissions.set(list(perms(apps, actions)))
            groups[label] = group
            self.stdout.write(self.style.SUCCESS(
                f"  group {'created' if created else 'updated'}: {label} "
                f"({group.permissions.count()} perms)"
            ))

        # Employees can apply for their own leave even though the group is view-only.
        apply_leave = Permission.objects.filter(
            content_type__app_label="leave", codename="add_leaverequest"
        ).first()
        if apply_leave:
            groups["Employee"].permissions.add(apply_leave)

        if opts.get("admin_username"):
            self._make_admin(company, groups["HR Manager"], opts)

        self.stdout.write(self.style.SUCCESS("Done."))

    def _make_admin(self, company, hr_manager_group, opts):
        username = opts["admin_username"]
        if not opts.get("admin_password"):
            raise CommandError("--admin-password is required with --admin-username.")

        if SkylinxUser.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'  admin "{username}" already exists - skipping creation.'
            ))
            return

        # NOTE: create_user (NOT superuser) on purpose -> middleware locks this
        # login to `company`; group perms give them HR-admin power inside it.
        user = SkylinxUser.objects.create_user(
            username=username, email=opts["admin_email"], password=opts["admin_password"]
        )
        user.is_staff = True
        user.save()
        user.groups.add(hr_manager_group)

        employee = Employee.objects.create(
            employee_user_id=user,
            employee_first_name=opts["admin_first_name"],
            employee_last_name=opts["admin_last_name"],
            email=opts["admin_email"],
        )
        # Employee.save() auto-creates a blank work-info row via signal; set the
        # company on it (update_or_create, never a duplicate).
        EmployeeWorkInformation.objects.update_or_create(
            employee_id=employee,
            defaults={"company_id": company, "email": opts["admin_email"]},
        )

        # Match createskylinxuser: ensure the notification bot exists.
        if not SkylinxUser.objects.filter(username="Skylinx Bot").exists():
            SkylinxUser.objects.create_user(username="Skylinx Bot", password=str(uuid.uuid4()))

        self.stdout.write(self.style.SUCCESS(
            f'  scoped admin created: {username} (locked to {company})'
        ))
