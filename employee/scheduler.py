from django.utils import timezone
import sys
from datetime import date, datetime, time, timedelta

from apscheduler.schedulers.background import BackgroundScheduler


def update_experience():
    from employee.models import EmployeeWorkInformation

    """
    This scheduled task to trigger the experience calculator
    to update the employee work experience
    """
    queryset = EmployeeWorkInformation.objects.filter(employee_id__is_active=True)
    for instance in queryset:
        instance.experience_calculator()
    return


def block_unblock_disciplinary():
    """
    Scheduled task to apply disciplinary actions and block/unblock employee accounts.
    """
    from base.models import EmployeeShiftSchedule
    from employee.models import DisciplinaryAction
    from skylinx_auth.models import SkylinxUser

    today = date.today()
    now = timezone.localtime().time()

    dis_actions = DisciplinaryAction.objects.select_related("action").prefetch_related(
        "employee_id"
    )

    for dis in dis_actions:
        if not dis.action.block_option:
            continue

        employees = dis.employee_id.exclude(employee_user_id__isnull=True)
        user_ids = list(employees.values_list("employee_user_id", flat=True))
        if not user_ids:
            continue

        if dis.action.action_type == "suspension":
            active = None

            if dis.days:
                start_date = dis.start_date
                end_date = start_date + timedelta(days=dis.days)
                if today >= end_date:
                    active = True
                elif today >= start_date:
                    active = False

            if dis.hours:
                if today != dis.start_date:
                    continue
                hour_str = dis.hours + ":00"
                hour_time = datetime.strptime(hour_str, "%H:%M:%S").time()

                for emp in employees:
                    if not emp.employee_work_info:
                        continue

                    shift = emp.employee_work_info.shift_id
                    shift_today = EmployeeShiftSchedule.objects.filter(
                        shift_id=shift, day__day=datetime.today().strftime("%A").lower()
                    ).first()
                    if not shift_today:
                        continue

                    st_time = shift_today.start_time
                    suspension_end_datetime = datetime.combine(
                        today, st_time
                    ) + timedelta(
                        hours=hour_time.hour,
                        minutes=hour_time.minute,
                        seconds=hour_time.second,
                    )
                    suspension_end_time = suspension_end_datetime.time()

                    if now >= suspension_end_time:
                        active = True
                    elif now >= st_time:
                        active = False

                    user = emp.employee_user_id
                    if user:
                        user.is_active = active
                        user.save()

            if dis.days and active is not None:
                SkylinxUser.objects.filter(id__in=user_ids).update(is_active=active)

        elif dis.action.action_type == "dismissal":
            if today >= dis.start_date:
                active = False
                SkylinxUser.objects.filter(id__in=user_ids).update(is_active=active)


def notify_probation_end():
    """
    Daily task: email HR (and the reporting manager) when an employee's probation
    period ends today, so they can confirm the employee.
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from employee.models import EmployeeWorkInformation

    today = date.today()
    ending = [
        wi
        for wi in EmployeeWorkInformation.objects.filter(
            employee_id__is_active=True,
            date_joining__isnull=False,
            probation_days__isnull=False,
        ).select_related("employee_id", "company_id", "reporting_manager_id")
        if wi.probation_end == today
    ]

    for wi in ending:
        emp = wi.employee_id
        recipients = set()

        mgr = wi.reporting_manager_id
        if mgr and mgr.get_mail():
            recipients.add(mgr.get_mail())

        # HR = users with employee.change_employee in the same company.
        # ponytail: per-user perm check; fine for a daily job over the handful
        # of employees whose probation ends on a given day.
        for hwi in EmployeeWorkInformation.objects.filter(
            company_id=wi.company_id
        ).select_related("employee_id__employee_user_id"):
            user = hwi.employee_id.employee_user_id
            if user and user.has_perm("employee.change_employee"):
                mail = hwi.employee_id.get_mail()
                if mail:
                    recipients.add(mail)

        if not recipients:
            continue

        send_mail(
            subject=f"Probation period ended: {emp.get_full_name()}",
            message=(
                f"The probation period for {emp.get_full_name()} ended on {today}. "
                "Please review and confirm their employment status."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=list(recipients),
            fail_silently=True,
        )


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell", "test"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_experience, "interval", hours=4)
    # ponytail: was seconds=60 (debug leftover) — disciplinary block/unblock is
    # date-range based, so hourly is ample and stops the per-minute DB load.
    scheduler.add_job(block_unblock_disciplinary, "interval", hours=1)
    scheduler.add_job(notify_probation_end, "cron", hour=8)
    scheduler.start()
