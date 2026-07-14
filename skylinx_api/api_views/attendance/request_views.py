"""Mobile attendance-approval flow (Kredily-style "Get Approval").

Employee: request approval for a day they were absent (creates a
`create_request` Attendance, HR notified in-app + email).
HR/manager: list pending requests, approve / reject, or directly mark an
absent employee present (auto-approved request) — employee notified both ways.
"""

import json
import threading
from datetime import date, datetime, timedelta

from django.core.mail import EmailMessage
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication

from attendance.models import Attendance
from attendance.methods.utils import shift_schedule_today
from attendance.views.requests import apply_attendance_request_approval
from base.models import CompanyLeaves, EmployeeShiftDay, Holidays
from employee.models import Employee
from notifications.signals import notify
from skylinx_api.auth import CompanyScopedJWTAuthentication
from base.rbac import hierarchy_rank


def _mail_async(to_email, subject, body):
    if not to_email:
        return
    def _send():
        try:
            EmailMessage(subject=subject, body=body, to=[to_email]).send(fail_silently=True)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _sec_to_time(sec):
    return (datetime.min + timedelta(seconds=int(sec or 0))).time()


def _shift_day(att_date):
    """EmployeeShiftDay rows are M2M company-scoped and may be invisible in
    the current company context — same .entire() fallback as check-in."""
    day_name = att_date.strftime("%A").lower()
    return (
        EmployeeShiftDay.objects.filter(day=day_name).first()
        or EmployeeShiftDay.objects.entire().filter(day=day_name).first()
        or EmployeeShiftDay.objects.entire().first()
    )


def _non_working_date_message(employee, att_date):
    if att_date > date.today():
        return "Future attendance cannot be marked."
    company = employee.get_company()
    holiday = Holidays.objects.entire().filter(
        start_date__lte=att_date,
        is_optional=False,
    ).filter(
        Q(end_date__gte=att_date)
        | Q(end_date__isnull=True, start_date=att_date)
    )
    if company:
        holiday = holiday.filter(Q(company_id=company) | Q(company_id__isnull=True))
    if holiday.exists():
        return "Attendance cannot be marked on a holiday."
    company_leaves = CompanyLeaves.objects.entire()
    if company:
        company_leaves = company_leaves.filter(
            Q(company_id=company) | Q(company_id__isnull=True)
        )
    try:
        from leave.methods import company_leave_dates_list
        if att_date in company_leave_dates_list(company_leaves, att_date.replace(day=1)):
            return "Attendance cannot be marked on an off day."
    except Exception:
        pass
    return None


def _hr_recipients(employee):
    """HR managers / admins of the employee's company (users with the
    attendance change perm), excluding the employee themself."""
    company = employee.get_company()
    recipients = []
    for emp in Employee.objects.filter(is_active=True):
        if emp.id == employee.id:
            continue
        if emp.get_company() != company:
            continue
        user = emp.employee_user_id
        if user and user.has_perm("attendance.change_attendance"):
            recipients.append(emp)
    return recipients


def _is_attendance_manager(user):
    return hierarchy_rank(user) <= 2


def _request_payload(a):
    return {
        "id": a.id,
        "employeeId": a.employee_id_id,
        "employeeName": a.employee_id.get_full_name(),
        "date": str(a.attendance_date),
        "checkIn": str(a.attendance_clock_in) if a.attendance_clock_in else None,
        "checkOut": str(a.attendance_clock_out) if a.attendance_clock_out else None,
        "description": a.request_description or "",
        "requestType": a.request_type,
        "pending": bool(a.is_validate_request),
        "approved": bool(a.is_validate_request_approved),
    }


class MobileAttendanceRequestAPIView(APIView):
    """GET: my attendance requests. POST: request approval for a date."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee"}, status=400)
        rows = Attendance.objects.filter(
            employee_id=employee,
            request_type__in=["create_request", "created_request", "update_request"],
        ).order_by("-attendance_date")[:60]
        return Response({"success": True, "data": [_request_payload(a) for a in rows]})

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee"}, status=400)

        date_str = request.data.get("date")
        try:
            att_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response({"success": False, "message": "Invalid or missing date (YYYY-MM-DD)."}, status=400)
        blocked = _non_working_date_message(employee, att_date)
        if blocked:
            return Response({"success": False, "message": blocked}, status=400)
        existing = Attendance.objects.filter(employee_id=employee, attendance_date=att_date).first()
        if existing:
            if existing.is_validate_request:
                return Response({"success": False, "message": "A request for this date is already pending."}, status=400)
            return Response({"success": False, "message": "Attendance already exists for this date."}, status=400)

        wi = getattr(employee, "employee_work_info", None)
        shift = wi.shift_id if wi else None
        if not shift:
            return Response({"success": False, "message": "No shift assigned — contact HR."}, status=400)

        day = _shift_day(att_date)
        if not day:
            return Response({"success": False, "message": "Shift schedule not configured."}, status=400)
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        check_in = str(request.data.get("checkIn") or "").strip()
        check_out = str(request.data.get("checkOut") or "").strip()
        try:
            in_time = datetime.strptime(check_in, "%H:%M").time() if check_in else _sec_to_time(start_sec)
            out_time = datetime.strptime(check_out, "%H:%M").time() if check_out else _sec_to_time(end_sec)
        except ValueError:
            return Response({"success": False, "message": "Times must be HH:MM."}, status=400)

        worked_sec = max(
            0,
            (datetime.combine(att_date, out_time) - datetime.combine(att_date, in_time)).total_seconds(),
        )
        worked_hour = f"{int(worked_sec // 3600):02d}:{int((worked_sec % 3600) // 60):02d}"

        attendance = Attendance(
            employee_id=employee,
            attendance_date=att_date,
            attendance_clock_in_date=att_date,
            attendance_clock_in=in_time,
            attendance_clock_out_date=att_date,
            attendance_clock_out=out_time,
            shift_id=shift,
            work_type_id=wi.work_type_id if wi else None,
            attendance_worked_hour=worked_hour,
            minimum_hour=minimum_hour,
            attendance_validated=False,
            is_validate_request=True,
            request_type="create_request",
            request_description=str(request.data.get("reason") or "").strip()[:255]
            or "Requested from mobile app",
        )
        attendance.save()

        # Notify HR (in-app + email)
        for hr in _hr_recipients(employee):
            if hr.employee_user_id:
                notify.send(
                    request.user,
                    recipient=hr.employee_user_id,
                    verb=f"{employee.get_full_name()} requested attendance approval for {att_date}",
                    redirect="/attendance/request-attendance-view/",
                    icon="time-outline",
                )
            _mail_async(
                hr.email,
                f"Attendance approval request — {employee.get_full_name()} ({att_date})",
                f"{employee.get_full_name()} has requested attendance approval for {att_date} "
                f"({in_time.strftime('%H:%M')} – {out_time.strftime('%H:%M')}).\n\n"
                f"Reason: {attendance.request_description}\n\n"
                "Review it from the Emplinx app or the web dashboard → Attendance → Requests.",
            )

        return Response(
            {"success": True, "message": "Approval request sent to HR.", "data": _request_payload(attendance)},
            status=201,
        )


class MobileAttendanceRequestAdminAPIView(APIView):
    """HR/manager: GET pending requests; POST {action: approve|reject} on one."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def get(self, request):
        if not _is_attendance_manager(request.user):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        rows = Attendance.objects.filter(is_validate_request=True).order_by("-attendance_date")[:100]
        return Response({"success": True, "data": [_request_payload(a) for a in rows]})

    def post(self, request, attendance_id):
        if not _is_attendance_manager(request.user):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        attendance = Attendance.objects.filter(id=attendance_id, is_validate_request=True).first()
        if not attendance:
            return Response({"success": False, "message": "Request not found."}, status=404)

        action = str(request.data.get("action") or "").lower()
        actor = request.user.employee_get
        employee = attendance.employee_id
        att_date = attendance.attendance_date

        if action == "approve":
            attendance = apply_attendance_request_approval(attendance, actor)
            verb = f"Your attendance for {att_date} was approved by {actor.get_full_name()}"
            mail_subject = f"Attendance approved for {att_date}"
            mail_body = (
                f"Hi {employee.employee_first_name},\n\n"
                f"Your attendance for {att_date} has been approved and recorded by "
                f"{actor.get_full_name()}.\n\n— Emplinx"
            )
        elif action == "reject":
            was_create = attendance.request_type == "create_request"
            attendance.is_validate_request_approved = False
            attendance.is_validate_request = False
            attendance.request_description = None
            attendance.requested_data = None
            attendance.request_type = None
            attendance.save()
            if was_create:
                attendance.delete()
            verb = f"Your attendance request for {att_date} was rejected"
            mail_subject = f"Attendance request rejected for {att_date}"
            mail_body = (
                f"Hi {employee.employee_first_name},\n\n"
                f"Your attendance request for {att_date} was rejected by "
                f"{actor.get_full_name()}. Contact HR if you believe this is a mistake.\n\n— Emplinx"
            )
        else:
            return Response({"success": False, "message": "action must be approve or reject."}, status=400)

        if employee.employee_user_id:
            notify.send(
                request.user,
                recipient=employee.employee_user_id,
                verb=verb,
                redirect="/attendance/view-my-attendance/",
                icon="checkmark-circle-outline" if action == "approve" else "close-circle-outline",
            )
        _mail_async(employee.email, mail_subject, mail_body)
        return Response({"success": True, "message": "Request approved." if action == "approve" else "Request rejected."})


class MobileMarkPresentAPIView(APIView):
    """HR/manager: mark an absent employee present for a date — creates the
    attendance and auto-approves it in one step. Employee notified + emailed."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def post(self, request):
        if not _is_attendance_manager(request.user):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        actor = request.user.employee_get

        employee = Employee.objects.filter(id=request.data.get("employeeId"), is_active=True).first()
        if not employee:
            return Response({"success": False, "message": "Employee not found."}, status=404)
        try:
            att_date = datetime.strptime(str(request.data.get("date")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response({"success": False, "message": "Invalid or missing date (YYYY-MM-DD)."}, status=400)
        blocked = _non_working_date_message(employee, att_date)
        if blocked:
            return Response({"success": False, "message": blocked}, status=400)
        if Attendance.objects.filter(employee_id=employee, attendance_date=att_date).exists():
            return Response({"success": False, "message": "Attendance already exists for this date."}, status=400)

        wi = getattr(employee, "employee_work_info", None)
        shift = wi.shift_id if wi else None
        if not shift:
            return Response({"success": False, "message": "Employee has no shift assigned."}, status=400)

        day = _shift_day(att_date)
        if not day:
            return Response({"success": False, "message": "Shift schedule not configured."}, status=400)
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        in_time, out_time = _sec_to_time(start_sec), _sec_to_time(end_sec)

        # Optional exact times ("Mark Exact Time" in the app): checkIn /
        # checkOut as "HH:MM". Either may be given alone — the other falls
        # back to the shift boundary above.
        def _parse_hhmm(key):
            raw = request.data.get(key)
            if raw in (None, ""):
                return None
            try:
                return datetime.strptime(str(raw), "%H:%M").time()
            except (ValueError, TypeError):
                raise ValueError(key)

        try:
            custom_in = _parse_hhmm("checkIn")
            custom_out = _parse_hhmm("checkOut")
        except ValueError as bad:
            return Response({"success": False, "message": f"Invalid {bad} (HH:MM)."}, status=400)
        if custom_in:
            in_time = custom_in
        if custom_out:
            out_time = custom_out
        if datetime.combine(att_date, out_time) <= datetime.combine(att_date, in_time):
            return Response({"success": False, "message": "Check-out must be after check-in."}, status=400)

        worked_sec = max(
            0,
            (datetime.combine(att_date, out_time) - datetime.combine(att_date, in_time)).total_seconds(),
        )
        worked_hour = f"{int(worked_sec // 3600):02d}:{int((worked_sec % 3600) // 60):02d}"

        attendance = Attendance(
            employee_id=employee,
            attendance_date=att_date,
            attendance_clock_in_date=att_date,
            attendance_clock_in=in_time,
            attendance_clock_out_date=att_date,
            attendance_clock_out=out_time,
            shift_id=shift,
            work_type_id=wi.work_type_id if wi else None,
            attendance_worked_hour=worked_hour,
            minimum_hour=minimum_hour,
            attendance_validated=False,
            is_validate_request=True,
            request_type="create_request",
            request_description=f"Marked present by {actor.get_full_name()}",
        )
        attendance.save()
        attendance = apply_attendance_request_approval(attendance, actor)

        if employee.employee_user_id:
            notify.send(
                request.user,
                recipient=employee.employee_user_id,
                verb=f"Your attendance for {att_date} was marked present by {actor.get_full_name()}",
                redirect="/attendance/view-my-attendance/",
                icon="checkmark-circle-outline",
            )
        _mail_async(
            employee.email,
            f"Attendance updated for {att_date}",
            f"Hi {employee.employee_first_name},\n\n"
            f"Your attendance for {att_date} was marked Present by {actor.get_full_name()}.\n\n— Emplinx",
        )
        return Response(
            {"success": True, "message": "Marked present.", "data": _request_payload(attendance)},
            status=201,
        )


class MobileTeamAttendanceStatusAPIView(APIView):
    """HR/manager: every active employee's Present/Absent status for a date
    (?date=YYYY-MM-DD, default today) — powers the app's Team Attendance view."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def get(self, request):
        if not _is_attendance_manager(request.user):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        date_str = request.query_params.get("date")
        try:
            target = (
                datetime.strptime(str(date_str), "%Y-%m-%d").date()
                if date_str
                else datetime.today().date()
            )
        except (ValueError, TypeError):
            return Response({"success": False, "message": "Invalid date (YYYY-MM-DD)."}, status=400)

        att_by_emp = {
            a.employee_id_id: a
            for a in Attendance.objects.filter(attendance_date=target).select_related()
        }
        rows = []
        for emp in Employee.objects.filter(is_active=True).select_related(
            "employee_work_info"
        ).order_by("employee_first_name"):
            a = att_by_emp.get(emp.id)
            rows.append({
                "employeeId": emp.id,
                "name": emp.get_full_name(),
                "avatar": emp.get_avatar(),
                "designation": getattr(
                    getattr(emp, "employee_work_info", None), "job_position_id", None
                ) and str(emp.employee_work_info.job_position_id) or "",
                "status": (
                    "pending" if (a and a.is_validate_request)
                    else "present" if a
                    else "absent"
                ),
                "checkIn": str(a.attendance_clock_in) if a and a.attendance_clock_in else None,
                "checkOut": str(a.attendance_clock_out) if a and a.attendance_clock_out else None,
                "attendanceId": a.id if a else None,
            })
        present = sum(1 for r in rows if r["status"] == "present")
        return Response({
            "success": True,
            "date": str(target),
            "present": present,
            "absent": sum(1 for r in rows if r["status"] == "absent"),
            "pending": sum(1 for r in rows if r["status"] == "pending"),
            "data": rows,
        })


class MobileMarkAbsentAPIView(APIView):
    """HR/manager: undo an attendance for a date (mark absent) — deletes the
    Attendance row so the day counts as absent again. Employee is notified."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def post(self, request):
        if not _is_attendance_manager(request.user):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        actor = request.user.employee_get
        employee = Employee.objects.filter(id=request.data.get("employeeId")).first()
        if not employee:
            return Response({"success": False, "message": "Employee not found."}, status=404)
        try:
            att_date = datetime.strptime(str(request.data.get("date")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response({"success": False, "message": "Invalid or missing date (YYYY-MM-DD)."}, status=400)
        attendance = Attendance.objects.filter(
            employee_id=employee, attendance_date=att_date
        ).first()
        if not attendance:
            return Response({"success": False, "message": "No attendance on this date."}, status=404)
        attendance.delete()
        if employee.employee_user_id:
            notify.send(
                request.user,
                recipient=employee.employee_user_id,
                verb=f"Your attendance for {att_date} was marked absent by {actor.get_full_name()}",
                redirect="/attendance/view-my-attendance/",
                icon="close-circle-outline",
            )
        _mail_async(
            employee.email,
            f"Attendance updated for {att_date}",
            f"Hi {employee.employee_first_name},\n\n"
            f"Your attendance for {att_date} was marked Absent by {actor.get_full_name()}. "
            "Contact HR if you believe this is a mistake.\n\n— Emplinx",
        )
        return Response({"success": True, "message": "Marked absent."})
