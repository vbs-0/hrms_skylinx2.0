import os
from datetime import date, datetime, timedelta
from django.core.files.storage import default_storage
from django.utils import timezone
from geopy.distance import geodesic
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from skylinx_api.auth import CompanyScopedJWTAuthentication

from attendance.models import Attendance, AttendanceActivity, EmployeeShiftDay, MobileAttendanceDetail, MobileLocationLog
from attendance.views.clock_in_out import (
    clock_in_attendance_and_activity,
    clock_out,
    clock_out_attendance_and_activity,
    missing_checkout_create,
)
from attendance.methods.utils import (
    employee_exists,
    shift_schedule_today,
    strtime_seconds,
    Request as AttendanceRequest
)
from facedetection.models import FaceDetection, EmployeeFaceDetection
from facedetection.face_matching import compare_faces, has_face
from geofencing.models import GeoFencing


def _geofence_exempt(employee):
    """Skip geofence checks entirely for: Hybrid/Work-From-Home employees
    (WorkType.geofence_exempt=True), or employees individually exempted on
    the company's GeoFencing settings (GeoFencing.exempted_employees)."""
    wi = getattr(employee, "employee_work_info", None)
    work_type = getattr(wi, "work_type_id", None) if wi else None
    if work_type and work_type.geofence_exempt:
        return True
    return GeoFencing.objects.filter(
        company_id=employee.get_company(), exempted_employees=employee
    ).exists()


def _just_exited_geofence(previous):
    return previous is not None and previous.within_geofence


def _company_alert_recipients(employee):
    """Users who should get location/geofence alerts for this employee:
    reporting manager + the employee's company's HR Managers and Company
    Admins. (Previously targeted is_superuser/is_staff — HR never got the
    alerts and they leaked across tenants.)"""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    from base.rbac import SEP

    User = get_user_model()
    recipients = set()
    wi = getattr(employee, "employee_work_info", None)
    rm = getattr(wi, "reporting_manager_id", None) if wi else None
    if rm is not None and getattr(rm, "employee_user_id", None):
        recipients.add(rm.employee_user_id)
    company = employee.get_company()
    if company:
        for g in Group.objects.filter(
            company_link__company=company, name__endswith=SEP + "HR Manager"
        ):
            recipients.update(g.user_set.all())
        recipients.update(
            User.objects.filter(
                groups__name="Company Admin",
                employee_get__employee_work_info__company_id=company,
            )
        )
    return recipients


class MobileCheckInAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "errorCode": "NOT_AN_EMPLOYEE"
            }, status=400)

        # 1. Parse GPS and Selfie Parameters
        selfie_file = request.FILES.get("selfie")
        latitude_str = request.data.get("latitude")
        longitude_str = request.data.get("longitude")
        accuracy_str = request.data.get("accuracy", "0")
        gps_enabled_str = request.data.get("gpsEnabled", "true")

        if not selfie_file:
            return Response({
                "success": False,
                "message": "Selfie image is required for check-in",
                "errorCode": "MISSING_SELFIE"
            }, status=400)

        if not latitude_str or not longitude_str:
            return Response({
                "success": False,
                "message": "GPS coordinates are required",
                "errorCode": "MISSING_COORDINATES"
            }, status=400)

        try:
            latitude = float(latitude_str)
            longitude = float(longitude_str)
            accuracy = float(accuracy_str)
            gps_enabled = gps_enabled_str.lower() == "true"
        except ValueError:
            return Response({
                "success": False,
                "message": "Invalid GPS coordinates formatting",
                "errorCode": "INVALID_GPS"
            }, status=400)

        # 2. Check Face Verification (Baseline Image comparison)
        company = employee.get_company()
        face_config = FaceDetection.objects.filter(company_id=company).first()
        
        if face_config and face_config.start:
            baseline = EmployeeFaceDetection.objects.filter(employee_id=employee).first()
            if not baseline or not baseline.image:
                # First check-in with face enabled: auto-enroll this selfie as
                # the employee's baseline — but only if it actually contains a
                # face, otherwise a wall/blank photo becomes the permanent
                # baseline and every future check-in trivially "matches" it.
                temp_path = default_storage.save("temp/enroll_selfie.jpg", selfie_file)
                temp_full_path = default_storage.path(temp_path)
                face_present = has_face(temp_full_path)
                if os.path.exists(temp_full_path):
                    os.remove(temp_full_path)
                if not face_present:
                    return Response({
                        "success": False,
                        "message": "No face detected in the photo. Please take a clear photo of your face.",
                        "errorCode": "NO_FACE_DETECTED"
                    }, status=400)

                if baseline is None:
                    baseline = EmployeeFaceDetection(employee_id=employee)
                selfie_file.seek(0)
                baseline.image = selfie_file
                baseline.save()
                # rewind so the same upload can still be stored as the attendance selfie
                selfie_file.seek(0)
            else:
                # Temporary save selfie to run verification
                temp_path = default_storage.save("temp/verification_selfie.jpg", selfie_file)
                temp_full_path = default_storage.path(temp_path)

                # Get path of baseline image
                baseline_path = baseline.image.path

                matched, similarity = compare_faces(baseline_path, temp_full_path)

                # Clean up temp file
                if os.path.exists(temp_full_path):
                    os.remove(temp_full_path)

                if not matched:
                    return Response({
                        "success": False,
                        "message": "Face verification failed. Please take a clear photo of your face.",
                        "errorCode": "FACE_VERIFICATION_FAILED"
                    }, status=400)

        # 3. Check Geofencing boundary
        within_geofence = True
        distance_meters = 0.0
        geofence = GeoFencing.objects.filter(company_id=company).first()

        if geofence and geofence.start and not _geofence_exempt(employee):
            geofence_center = (geofence.latitude, geofence.longitude)
            employee_loc = (latitude, longitude)
            try:
                distance_meters = geodesic(geofence_center, employee_loc).meters
                if distance_meters > geofence.radius_in_meters:
                    within_geofence = False
            except Exception as e:
                # Log error and default to inside geofence if geodesic fails
                print(f"Geopy calculation error: {e}")
                pass

            if not within_geofence and geofence.enforce:
                return Response({
                    "success": False,
                    "message": "You are outside the allowed check-in zone.",
                    "errorCode": "OUTSIDE_GEOFENCE",
                    "data": {"distanceFromCenterMeters": distance_meters},
                }, status=400)

        # 4. Perform check-in (Sync with EMPLINX Core Shift/Attendance logic)
        # Canonical clock state = an OPEN AttendanceActivity (the same thing the app
        # shows from /attendance/my/). check_online() instead looked at a 2-day
        # Attendance window, so a forgotten checkout YESTERDAY blocked today's
        # check-in while the app's today-only view said "not checked in" -> the
        # reported "already checked in but home says not checked in" mismatch.
        open_activity = AttendanceActivity.objects.filter(
            employee_id=employee, clock_out__isnull=True
        ).order_by("-id").first()
        if open_activity:
            if open_activity.attendance_date >= date.today():
                return Response({
                    "success": False,
                    "message": "Already checked-in",
                    "errorCode": "ALREADY_CHECKED_IN"
                }, status=400)
            # Stale open activity from a previous day (forgot to check out) ->
            # auto-close it so the user isn't locked out, then check in fresh
            # today. Close it directly via the pure helper (no anomaly side
            # effects) and flag it as a "Forgot to Checkout" anomaly instead
            # of running it through the normal clock_out() view, which would
            # compare TODAY's time against YESTERDAY's shift end and wrongly
            # log it as an early-out.
            closed_attendance = clock_out_attendance_and_activity(
                employee=employee,
                date_today=date.today(),
                now=timezone.localtime().strftime("%H:%M"),
                out_datetime=timezone.now(),
            )
            if closed_attendance:
                missing_checkout_create(closed_attendance)
            else:
                open_activity.clock_out = timezone.now()
                open_activity.clock_out_date = date.today()
                open_activity.out_datetime = timezone.now()
                open_activity.save()

        work_info = employee.employee_work_info if hasattr(employee, "employee_work_info") else None
        if not work_info or not work_info.shift_id:
            return Response({
                "success": False,
                "message": "You don't have shift information filled",
                "errorCode": "NO_SHIFT_INFO"
            }, status=400)

        shift = work_info.shift_id
        date_today = date.today()
        attendance_date = date_today
        day_name = date_today.strftime("%A").lower()
        # Day-of-week rows are global lookup data; the company M2M may not be linked
        # for this tenant, so fall back to the unscoped row to avoid a None day.
        day = (
            EmployeeShiftDay.objects.filter(day=day_name).first()
            or EmployeeShiftDay.objects.entire().filter(day=day_name).first()
            or EmployeeShiftDay.objects.entire().first()
        )

        now_str = timezone.localtime().strftime("%H:%M")
        now_sec = strtime_seconds(now_str)
        mid_day_sec = strtime_seconds("12:00")

        if day:
            minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                day=day, shift=shift
            )
            has_schedule_today = day.day_schedule.filter(shift_id=shift).exists()
        else:
            minimum_hour, start_time_sec, end_time_sec = "00:00", 0, 0
            has_schedule_today = False

        # Handle night shift logic
        if start_time_sec > end_time_sec:
            if mid_day_sec > now_sec:
                date_yesterday = date_today - timedelta(days=1)
                day_yesterday_name = date_yesterday.strftime("%A").lower()
                day_yesterday = (
                    EmployeeShiftDay.objects.filter(day=day_yesterday_name).first()
                    or EmployeeShiftDay.objects.entire().filter(day=day_yesterday_name).first()
                )
                if day_yesterday:
                    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                        day=day_yesterday, shift=shift
                    )
                    attendance_date = date_yesterday
                    day = day_yesterday
                    has_schedule_today = day.day_schedule.filter(shift_id=shift).exists()

        if not has_schedule_today:
            return Response({
                "success": False,
                "message": "You are not scheduled to work today",
                "errorCode": "NO_SHIFT_SCHEDULED_TODAY"
            }, status=400)

        # Enforce the shift time window: check-in is allowed from
        # (shift start - grace) until shift end, and blocked outside it.
        # ponytail: 30-min grace before start; bump GRACE_SECS if HR wants a
        # wider early-clock-in window.
        GRACE_SECS = 30 * 60
        start_with_grace = start_time_sec - GRACE_SECS
        if start_time_sec > end_time_sec:
            # night shift wraps midnight: valid in the evening (>= start-grace)
            # OR in the early hours before shift end (<= end).
            in_shift_window = now_sec >= start_with_grace or now_sec <= end_time_sec
        else:
            in_shift_window = start_with_grace <= now_sec <= end_time_sec
        if not in_shift_window:
            return Response({
                "success": False,
                "message": "Check-in is only allowed during your shift hours.",
                "errorCode": "OUTSIDE_SHIFT_HOURS",
            }, status=400)

        # Create Core Attendance Activity
        datetime_now = timezone.now()
        clock_in_attendance_and_activity(
            employee=employee,
            date_today=date_today,
            attendance_date=attendance_date,
            day=day,
            now=now_str,
            shift=shift,
            minimum_hour=minimum_hour,
            start_time=start_time_sec,
            end_time=end_time_sec,
            in_datetime=datetime_now,
        )

        # 5. Save Mobile Extra Details
        activity = AttendanceActivity.objects.filter(employee_id=employee).order_by("-id").first()
        if activity:
            MobileAttendanceDetail.objects.create(
                attendance_activity=activity,
                check_in_selfie=selfie_file,
                check_in_lat=latitude,
                check_in_lng=longitude,
                within_geofence=within_geofence
            )

        if not within_geofence:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification
            
            admins = _company_alert_recipients(employee)
            user_ct = ContentType.objects.get_for_model(request.user)
            
            for admin in admins:
                Notification.objects.get_or_create(
                    recipient=admin,
                    actor_content_type=user_ct,
                    actor_object_id=str(request.user.id),
                    verb="Outside Geofence",
                    description=f"{employee.employee_first_name} {employee.employee_last_name} checked in outside the geofence zone.",
                    level="danger"
                )

        return Response({
            "success": True,
            "message": "Check-in successful",
            "data": {
                "attendanceId": str(activity.id) if activity else "1",
                "withinGeofence": within_geofence,
                "distanceFromCenterMeters": distance_meters,
                "status": "present" if within_geofence else "outside_geofence",
                "liveTrackingEnabled": True
            }
        }, status=201)


class MobileCheckOutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "errorCode": "NOT_AN_EMPLOYEE"
            }, status=400)

        # Allow checkout only when there is an OPEN AttendanceActivity (the real
        # clock state shown in the app), not check_online()'s 2-day window.
        open_activity = AttendanceActivity.objects.filter(
            employee_id=employee, clock_out__isnull=True
        ).order_by("-id").first()
        if not open_activity:
            return Response({
                "success": False,
                "message": "Already checked-out",
                "errorCode": "ALREADY_CHECKED_OUT"
            }, status=400)

        selfie_file = request.FILES.get("selfie")
        latitude_str = request.data.get("latitude")
        longitude_str = request.data.get("longitude")

        if not selfie_file:
            return Response({
                "success": False,
                "message": "Selfie image is required for check-out",
                "errorCode": "MISSING_SELFIE"
            }, status=400)

        if not latitude_str or not longitude_str:
            return Response({
                "success": False,
                "message": "GPS coordinates are required",
                "errorCode": "MISSING_COORDINATES"
            }, status=400)

        try:
            latitude = float(latitude_str)
            longitude = float(longitude_str)
        except ValueError:
            return Response({
                "success": False,
                "message": "Invalid GPS coordinates formatting",
                "errorCode": "INVALID_GPS"
            }, status=400)

        # Check Face Verification (Baseline Image comparison)
        company = employee.get_company()
        face_config = FaceDetection.objects.filter(company_id=company).first()
        
        if face_config and face_config.start:
            baseline = EmployeeFaceDetection.objects.filter(employee_id=employee).first()
            if not baseline or not baseline.image:
                # No baseline yet (face enabled after this employee's first check-in):
                # auto-enroll instead of blocking check-out.
                if baseline is None:
                    baseline = EmployeeFaceDetection(employee_id=employee)
                baseline.image = selfie_file
                baseline.save()
                # rewind so the same upload can still be stored as the attendance selfie
                selfie_file.seek(0)
            else:
                # Temporary save selfie to run verification
                temp_path = default_storage.save("temp/verification_checkout_selfie.jpg", selfie_file)
                temp_full_path = default_storage.path(temp_path)

                # Get path of baseline image
                baseline_path = baseline.image.path

                matched, similarity = compare_faces(baseline_path, temp_full_path)

                # Clean up temp file
                if os.path.exists(temp_full_path):
                    os.remove(temp_full_path)

                if not matched:
                    return Response({
                        "success": False,
                        "message": "Face verification failed. Please take a clear photo of your face.",
                        "errorCode": "FACE_VERIFICATION_FAILED"
                    }, status=400)

        # Check Geofencing boundary
        within_geofence = True
        distance_meters = 0.0
        geofence = GeoFencing.objects.filter(company_id=company).first()

        if geofence and geofence.start and not _geofence_exempt(employee):
            geofence_center = (geofence.latitude, geofence.longitude)
            employee_loc = (latitude, longitude)
            try:
                distance_meters = geodesic(geofence_center, employee_loc).meters
                if distance_meters > geofence.radius_in_meters:
                    within_geofence = False
            except Exception:
                pass

            if not within_geofence and geofence.enforce:
                return Response({
                    "success": False,
                    "message": "You are outside the allowed check-out zone.",
                    "errorCode": "OUTSIDE_GEOFENCE",
                    "data": {"distanceFromCenterMeters": distance_meters},
                }, status=400)

        # Perform checkout
        current_date = date.today()
        current_time = timezone.localtime().time()
        current_datetime = timezone.now()

        # Call Django Core check-out
        clock_out(
            AttendanceRequest(
                user=request.user,
                date=current_date,
                time=current_time,
                datetime=current_datetime,
            )
        )

        # Update Mobile Extra Details
        activity = AttendanceActivity.objects.filter(employee_id=employee, clock_out__isnull=False).order_by("-id").first()
        if activity:
            detail, created = MobileAttendanceDetail.objects.get_or_create(attendance_activity=activity)
            detail.check_out_selfie = selfie_file
            detail.check_out_lat = latitude
            detail.check_out_lng = longitude
            detail.check_out_within_geofence = within_geofence
            detail.save()

        if not within_geofence:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification
            
            admins = _company_alert_recipients(employee)
            user_ct = ContentType.objects.get_for_model(request.user)
            
            for admin in admins:
                Notification.objects.get_or_create(
                    recipient=admin,
                    actor_content_type=user_ct,
                    actor_object_id=str(request.user.id),
                    verb="Outside Geofence",
                    description=f"{employee.employee_first_name} {employee.employee_last_name} checked out outside the geofence zone.",
                    level="danger"
                )

        return Response({
            "success": True,
            "message": "Check-out successful",
            "data": {
                "attendanceId": str(activity.id) if activity else "1",
                "withinGeofence": within_geofence,
                "distanceFromCenterMeters": distance_meters
            }
        }, status=201)


class MobileLocationLogAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "errorCode": "NOT_AN_EMPLOYEE"
            }, status=400)

        # Gate on subscription plan
        company = employee.get_company()
        if not (company and hasattr(company, 'subscription') and company.subscription.has_feature("live_location")):
            return Response({
                "success": False,
                "message": "Live location tracking is not enabled for your plan.",
                "errorCode": "FEATURE_LOCKED"
            }, status=403)

        latitude = float(request.data.get("latitude", 0))
        longitude = float(request.data.get("longitude", 0))
        accuracy = float(request.data.get("accuracy", 0))
        gps_enabled_val = request.data.get("gpsEnabled", True)
        # Handle string type or boolean type gpsEnabled
        if isinstance(gps_enabled_val, str):
            gps_enabled = gps_enabled_val.lower() == "true"
        else:
            gps_enabled = bool(gps_enabled_val)

        # Only meaningful mid-shift — an open (not clocked-out) attendance activity.
        is_clocked_in = AttendanceActivity.objects.filter(
            employee_id=employee, out_datetime__isnull=True
        ).exists()

        within_geofence = True
        if is_clocked_in and not _geofence_exempt(employee):
            geofence = GeoFencing.objects.filter(company_id=company).first()
            if geofence:
                try:
                    distance_meters = geodesic(
                        (geofence.latitude, geofence.longitude), (latitude, longitude)
                    ).meters
                    within_geofence = distance_meters <= geofence.radius_in_meters
                except Exception:
                    within_geofence = True

        log = MobileLocationLog.objects.create(
            employee=employee,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            gps_enabled=gps_enabled,
            within_geofence=within_geofence,
            captured_at=timezone.now()
        )

        if not gps_enabled:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification

            admins = _company_alert_recipients(employee)
            user_ct = ContentType.objects.get_for_model(request.user)

            for admin in admins:
                Notification.objects.get_or_create(
                    recipient=admin,
                    actor_content_type=user_ct,
                    actor_object_id=str(request.user.id),
                    verb="GPS Off",
                    description=f"{employee.employee_first_name} {employee.employee_last_name} turned off GPS location services at {timezone.localtime().strftime('%I:%M %p')}.",
                    level="warning"
                )

        # Alert only on the inside->outside transition, not on every ping while
        # already outside — otherwise HR gets spammed once per ping interval.
        if is_clocked_in and not within_geofence:
            previous = (
                MobileLocationLog.objects.filter(employee=employee)
                .exclude(id=log.id)
                .order_by("-captured_at")
                .first()
            )
            just_exited = _just_exited_geofence(previous)
            if just_exited:
                from django.contrib.contenttypes.models import ContentType
                from notifications.models import Notification

                admins = _company_alert_recipients(employee)
                user_ct = ContentType.objects.get_for_model(request.user)
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        actor_content_type=user_ct,
                        actor_object_id=str(request.user.id),
                        verb="Left Geofence",
                        description=f"{employee.employee_first_name} {employee.employee_last_name} left the geofence zone mid-shift at {timezone.localtime().strftime('%I:%M %p')}.",
                        level="danger"
                    )

        return Response({
            "success": True,
            "message": "Location logged",
            "data": {
                "id": str(log.id),
                "withinGeofence": within_geofence
            }
        }, status=201)


def geofence_distance_meters(geofence, lat, lng):
    """Distance from a stored check-in/out point to the geofence center, or
    None when there's nothing to measure (no geofence / no coords). History
    endpoints previously omitted this entirely, so the app rendered the
    null as a literal 'nullm outside'."""
    if not geofence or lat is None or lng is None:
        return None
    try:
        return round(geodesic((geofence.latitude, geofence.longitude), (lat, lng)).meters, 1)
    except Exception:
        return None


class MobileAttendanceHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "data": []
            }, status=400)

        geofence = GeoFencing.objects.filter(company_id=employee.get_company()).first()

        date_str = request.query_params.get("date")
        month_str = request.query_params.get("month")  # YYYY-MM — whole month

        # Load Attendance activities
        activities = AttendanceActivity.objects.filter(employee_id=employee)
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                activities = activities.filter(attendance_date=target_date)
            except ValueError:
                pass
        elif month_str:
            try:
                month_start = datetime.strptime(month_str, "%Y-%m").date()
                activities = activities.filter(
                    attendance_date__year=month_start.year,
                    attendance_date__month=month_start.month,
                )
            except ValueError:
                pass
        else:
            # Default to last 30 days
            start_date = date.today() - timedelta(days=30)
            activities = activities.filter(attendance_date__gte=start_date)

        activities = activities.order_by("-attendance_date", "-clock_in")

        # Map to Flutter AttendanceEvent objects format
        events = []
        for act in activities:
            detail = getattr(act, "mobile_detail", None)

            # Reverse-chronological WITHIN an activity: emit Check Out BEFORE Check
            # In so the app's "latest event" (_todayEvents.first) is the check-out
            # once you've clocked out. Emitting check-in first made the home screen
            # read "Checked In" even after a completed checkout (the clumsy state).
            if act.out_datetime:
                events.append({
                    "id": f"{act.id}_out",
                    "userId": str(request.user.id),
                    "eventType": "check_out",
                    "selfieUrl": request.build_absolute_uri(detail.check_out_selfie.url) if (detail and detail.check_out_selfie) else None,
                    "latitude": detail.check_out_lat if detail else None,
                    "longitude": detail.check_out_lng if detail else None,
                    "withinGeofence": detail.check_out_within_geofence if detail else True,
                    "distanceFromCenterMeters": geofence_distance_meters(
                        geofence,
                        detail.check_out_lat if detail else None,
                        detail.check_out_lng if detail else None,
                    ),
                    "gpsEnabled": True,
                    "capturedAt": act.out_datetime.isoformat(),
                    "createdAt": act.out_datetime.isoformat()
                })

            if act.in_datetime:
                events.append({
                    "id": f"{act.id}_in",
                    "userId": str(request.user.id),
                    "eventType": "check_in",
                    "selfieUrl": request.build_absolute_uri(detail.check_in_selfie.url) if (detail and detail.check_in_selfie) else None,
                    "latitude": detail.check_in_lat if detail else None,
                    "longitude": detail.check_in_lng if detail else None,
                    "withinGeofence": detail.within_geofence if detail else True,
                    "distanceFromCenterMeters": geofence_distance_meters(
                        geofence,
                        detail.check_in_lat if detail else None,
                        detail.check_in_lng if detail else None,
                    ),
                    "gpsEnabled": True,
                    "capturedAt": act.in_datetime.isoformat(),
                    "createdAt": act.created_at.isoformat()
                })

        return Response({
            "success": True,
            "message": "Logs retrieved",
            "data": events
        }, status=200)


class MobileCheckInEligibilityAPIView(APIView):
    """
    GET — tells the app upfront (before the camera/face flow) whether a
    check-in would be accepted right now. Mirrors the validation gates in
    MobileCheckInAPIView but performs NO writes (a stale open activity from
    a previous day is treated as eligible — the real check-in auto-closes it).
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    def get(self, request):
        employee = getattr(request.user, "employee_get", None)
        if not employee:
            return Response({"eligible": False, "message": "Employee profile not found", "errorCode": "NO_EMPLOYEE"}, status=200)

        open_activity = AttendanceActivity.objects.filter(
            employee_id=employee, clock_out__isnull=True
        ).order_by("-id").first()
        if open_activity and open_activity.attendance_date >= date.today():
            return Response({"eligible": False, "message": "Already checked-in", "errorCode": "ALREADY_CHECKED_IN"}, status=200)

        work_info = employee.employee_work_info if hasattr(employee, "employee_work_info") else None
        if not work_info or not work_info.shift_id:
            return Response({"eligible": False, "message": "You don't have shift information filled", "errorCode": "NO_SHIFT_INFO"}, status=200)

        shift = work_info.shift_id
        date_today = date.today()
        day_name = date_today.strftime("%A").lower()
        day = (
            EmployeeShiftDay.objects.filter(day=day_name).first()
            or EmployeeShiftDay.objects.entire().filter(day=day_name).first()
            or EmployeeShiftDay.objects.entire().first()
        )

        now_sec = strtime_seconds(timezone.localtime().strftime("%H:%M"))
        mid_day_sec = strtime_seconds("12:00")

        if day:
            _, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)
            has_schedule_today = day.day_schedule.filter(shift_id=shift).exists()
        else:
            start_time_sec, end_time_sec = 0, 0
            has_schedule_today = False

        # night shift: before noon, yesterday's shift may still be running
        if start_time_sec > end_time_sec and mid_day_sec > now_sec:
            date_yesterday = date_today - timedelta(days=1)
            day_yesterday = (
                EmployeeShiftDay.objects.filter(day=date_yesterday.strftime("%A").lower()).first()
                or EmployeeShiftDay.objects.entire().filter(day=date_yesterday.strftime("%A").lower()).first()
            )
            if day_yesterday:
                _, start_time_sec, end_time_sec = shift_schedule_today(day=day_yesterday, shift=shift)
                has_schedule_today = day_yesterday.day_schedule.filter(shift_id=shift).exists()

        if not has_schedule_today:
            return Response({"eligible": False, "message": "You are not scheduled to work today", "errorCode": "NO_SHIFT_SCHEDULED_TODAY"}, status=200)

        GRACE_SECS = 30 * 60
        start_with_grace = start_time_sec - GRACE_SECS
        if start_time_sec > end_time_sec:
            in_shift_window = now_sec >= start_with_grace or now_sec <= end_time_sec
        else:
            in_shift_window = start_with_grace <= now_sec <= end_time_sec
        if not in_shift_window:
            return Response({"eligible": False, "message": "Check-in is only allowed during your shift hours.", "errorCode": "OUTSIDE_SHIFT_HOURS"}, status=200)

        return Response({"eligible": True, "message": "OK", "errorCode": None}, status=200)


class MobileWeatherAPIView(APIView):
    """
    GET — current weather for the employee's company city, via the free
    Open-Meteo APIs (no key needed). Geocoded coordinates and the weather
    itself are cached (24h / 30min) so we hit Open-Meteo rarely.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CompanyScopedJWTAuthentication, SessionAuthentication]

    WMO = {
        0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
        61: "Light Rain", 63: "Rain", 65: "Heavy Rain", 66: "Freezing Rain",
        67: "Freezing Rain", 71: "Snow", 73: "Snow", 75: "Heavy Snow",
        77: "Snow", 80: "Showers", 81: "Showers", 82: "Heavy Showers",
        85: "Snow Showers", 86: "Snow Showers", 95: "Thunderstorm",
        96: "Thunderstorm", 99: "Thunderstorm",
    }

    def get(self, request):
        import requests as _requests
        from django.core.cache import cache

        employee = getattr(request.user, "employee_get", None)
        wi = getattr(employee, "employee_work_info", None) if employee else None
        company = getattr(wi, "company_id", None) if wi else None
        city = (getattr(company, "city", "") or "").strip()
        country = (getattr(company, "country", "") or "").strip()

        # Preferred location source: the company's geofence — exact office
        # coordinates, no geocoding needed. City text is the fallback for
        # companies without a geofence configured.
        geofence = getattr(company, "geo_fencing", None) if company else None
        coords = None
        if geofence and geofence.latitude and geofence.longitude:
            coords = {"lat": geofence.latitude, "lon": geofence.longitude}

        if not coords and not city:
            return Response({"success": False, "message": "No company location configured"}, status=200)

        loc_tag = (
            f"{coords['lat']:.3f}_{coords['lon']:.3f}" if coords else f"{city}_{country}"
        )
        weather_key = f"mobile_weather_{loc_tag}".lower().replace(" ", "_")
        cached = cache.get(weather_key)
        if cached:
            return Response(cached, status=200)

        try:
            if not coords:
                geo_key = f"mobile_geocode_{city}_{country}".lower().replace(" ", "_")
                coords = cache.get(geo_key)
                if not coords:
                    geo = _requests.get(
                        "https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": city, "count": 1},
                        timeout=6,
                    ).json()
                    results = geo.get("results") or []
                    if not results:
                        return Response({"success": False, "message": "City not found"}, status=200)
                    coords = {"lat": results[0]["latitude"], "lon": results[0]["longitude"]}
                    cache.set(geo_key, coords, 60 * 60 * 24)

            wx = _requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "current": "temperature_2m,weather_code",
                },
                timeout=6,
            ).json()
            current = wx.get("current") or {}
            code = int(current.get("weather_code", 0))
            payload = {
                "success": True,
                "tempC": round(float(current.get("temperature_2m", 0))),
                "description": self.WMO.get(code, "—"),
                "weatherCode": code,
                "city": city or getattr(company, "company", ""),
            }
            cache.set(weather_key, payload, 60 * 30)
            return Response(payload, status=200)
        except Exception:
            return Response({"success": False, "message": "Weather unavailable"}, status=200)
