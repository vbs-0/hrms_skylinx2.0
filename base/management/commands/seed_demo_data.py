"""
seed_demo_data

One command to get a realistic, ready-to-login test database:

    python manage.py seed_demo_data            # populate dummy data (append)
    python manage.py seed_demo_data --reset    # WIPE db first, then populate

It loads the bundled demo fixtures (employees, work info, etc. via
load_demo_data), wires up user groups with real members + permissions, and
sets up known demo logins. Group members are only ever real Employees that
have a linked user, so the "Total N users but the assign modal is empty"
orphan bug (badge counts auth users, picker reads Employees) cannot happen.

Demo logins after running:
    admin / admin123      (superuser)
    hrmanager / 123456    (HR Manager group)
    manager / 123456      (Manager group)
    emp1, emp2, ... / 123456  (Employee group)
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand

from employee.models import Employee

User = get_user_model()

DEMO_PW = "123456"
ADMIN_PW = "admin123"

# group name -> apps whose permissions it gets (view/add/change[/delete])
GROUP_SPEC = {
    "HR Manager": {
        "apps": ["employee", "attendance", "leave", "payroll", "recruitment"],
        "include_delete": True,
    },
    "Manager": {"apps": ["attendance", "leave"], "include_delete": False},
    "Employee": {"apps": ["leave"], "include_delete": False},
}


class Command(BaseCommand):
    help = (
        "Populate the database with demo data for testing "
        "(employees, groups with members, and known demo logins). "
        "Use --reset to wipe the database first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Flush the entire database before populating (full reset).",
        )
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Do not prompt for confirmation.",
        )

    def handle(self, *args, **options):
        # 1. Load the demo fixtures (load_demo_data handles --flush + date shifting).
        load_args = ["load_demo_data"]
        if options["reset"]:
            load_args.append("--flush")
        if not options["interactive"]:
            load_args.append("--no-input")
        call_command(*load_args)

        # 2. Create the groups with permissions.
        self.stdout.write("Setting up user groups...")
        for group_name, spec in GROUP_SPEC.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            actions = ["view", "add", "change"] + (
                ["delete"] if spec["include_delete"] else []
            )
            perms = Permission.objects.filter(
                content_type__app_label__in=spec["apps"],
                codename__regex=r"^(" + "|".join(actions) + ")_",
            )
            group.permissions.set(perms)

        # 3. Friendly demo logins. Only non-superuser employees with a linked
        #    user become members, so group membership is always consistent.
        emps = [
            e
            for e in Employee.objects.filter(employee_user_id__isnull=False).order_by("id")
            if not e.employee_user_id.is_superuser
        ]

        admin = User.objects.filter(is_superuser=True).order_by("id").first()
        if admin:
            admin.username = "admin"
            admin.set_password(ADMIN_PW)
            admin.save()

        # first employee -> HR Manager, second -> Manager, rest -> Employee
        roles = []
        if emps:
            roles.append((emps[0], "hrmanager", "HR Manager"))
        if len(emps) > 1:
            roles.append((emps[1], "manager", "Manager"))
        for i, emp in enumerate(emps[2:], start=1):
            roles.append((emp, f"emp{i}", "Employee"))

        for emp, username, group_name in roles:
            user = emp.employee_user_id
            user.username = username
            user.set_password(DEMO_PW)
            user.groups.clear()
            user.groups.add(Group.objects.get(name=group_name))
            user.save()

        # 4. Summary.
        self.stdout.write(self.style.SUCCESS("\nDemo logins:"))
        if admin:
            self.stdout.write(f"  admin / {ADMIN_PW}  (superuser)")
        for emp, username, group_name in roles:
            self.stdout.write(f"  {username} / {DEMO_PW}  ({group_name})")
        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {len(roles)} demo employee account(s) set up.")
        )
