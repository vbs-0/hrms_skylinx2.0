from base.rbac import is_platform_owner
from skylinx.skylinx_middlewares import set_selected_company
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from employee.models import Employee, EmployeeWorkInformation
from base.models import Company, EmployeeShift, EmployeeShiftDay
from geofencing.models import GeoFencing

def get_mobile_user_data(user):
    """
    Helper to serialize user and employee shift details into the JSON structure
    expected by the standalone Flutter application.
    """
    try:
        employee = user.employee_get
    except Exception:
        employee = None

    role = "employee"
    if is_platform_owner(user) or user.has_perm("employee.add_employee"):
        role = "admin"

    profile_data = None
    if employee:
        try:
            # Fetch shift information
            shift_data = None
            work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
            shift = work_info.shift_id if work_info else None

            if shift:
                # Query active days for this shift. Use .entire() (unscoped):
                # EmployeeShiftDay rows are plain day labels shared across the
                # schedule, and their company_id M2M is often left unassigned
                # (e.g. a day added later), so the company-scoped manager
                # silently drops those days — Saturday vanished this way.
                # The shift itself already came from the user's own work info.
                active_days_list = []
                s_days = EmployeeShiftDay.objects.entire().filter(day_schedule__shift_id=shift)
                for sd in s_days:
                    day_name = sd.day.capitalize()[:3]
                    if day_name not in active_days_list:
                        active_days_list.append(day_name)
                day_order = {
                    day: index
                    for index, day in enumerate(
                        ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
                    )
                }
                active_days_list.sort(
                    key=lambda day: day_order.get(day, len(day_order))
                )

                # Fetch company geofence details
                company = employee.get_company()
                geofence_radius = 100
                office_lat = None
                office_lng = None
                office_address = None
                geofence_enabled = False
                face_enabled = False
                if company:
                    gf = GeoFencing.objects.filter(company_id=company).first()
                    if gf:
                        geofence_radius = gf.radius_in_meters
                        office_lat = gf.latitude
                        office_lng = gf.longitude
                        geofence_enabled = gf.start
                        try:
                            office_address = str(company.address) if hasattr(company, 'address') else None
                        except Exception:
                            pass
                    
                    from facedetection.models import FaceDetection
                    fd = FaceDetection.objects.filter(company_id=company).first()
                    if fd:
                        face_enabled = fd.start

                # Get first schedule for start/end times
                first_schedule = shift.employeeshiftschedule_set.first()
                auto_punch_out_enabled = shift.employeeshiftschedule_set.filter(is_auto_punch_out_enabled=True).exists()
                shift_data = {
                    "id": str(shift.id),
                    "name": shift.employee_shift,
                    "startTime": first_schedule.start_time.strftime("%H:%M") if first_schedule else "09:00",
                    "endTime": first_schedule.end_time.strftime("%H:%M") if first_schedule else "18:00",
                    "reminderIntervalMinutes": 60,
                    "geofenceRadiusMeters": geofence_radius,
                    "officeLat": office_lat,
                    "officeLng": office_lng,
                    "officeAddress": office_address,
                    "geofenceEnabled": geofence_enabled,
                    "faceEnabled": face_enabled,
                    "autoPunchOutEnabled": auto_punch_out_enabled,
                    "activeDays": ",".join(active_days_list) if active_days_list else "Mon,Tue,Wed,Thu,Fri"
                }

            # Get department safely
            dept = None
            job_title = None
            try:
                if work_info and work_info.department_id:
                    dept = str(work_info.department_id.department)
                if work_info and work_info.job_position_id:
                    job_title = str(work_info.job_position_id.job_position)
            except Exception:
                pass

            # Check subscription plan first
            subscription_enabled = False
            company = employee.get_company()
            if company and hasattr(company, 'subscription'):
                subscription_enabled = company.subscription.has_feature("live_location")
            
            # Check owner's permission (from settings)
            owner_permission_enabled = True
            import os
            import json
            from django.conf import settings
            settings_dir = os.path.join(settings.MEDIA_ROOT, "company_settings")
            settings_path = os.path.join(settings_dir, f"settings_{company.id if company else 0}.json")
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r") as f:
                        data = json.load(f)
                        owner_permission_enabled = data.get("trackingEnabled", True)
                except Exception:
                    pass
            
            is_tracking_enabled = subscription_enabled and owner_permission_enabled

            reporting_manager = None
            try:
                rm = work_info.reporting_manager_id if work_info else None
                if rm:
                    reporting_manager = {
                        "id": str(rm.id),
                        "name": rm.get_full_name(),
                        "avatar": rm.get_avatar(),
                        "jobTitle": str(rm.employee_work_info.job_position_id)
                        if getattr(getattr(rm, "employee_work_info", None), "job_position_id", None)
                        else None,
                    }
            except Exception:
                pass

            profile_data = {
                "id": str(employee.id),
                "employeeCode": employee.badge_id or f"EMP{employee.id}",
                "profileUrl": employee.get_image() or None,
                "department": dept,
                "jobTitle": job_title,
                "reportingManager": reporting_manager,
                "shiftId": str(shift.id) if shift else None,
                "isTrackingEnabled": is_tracking_enabled,
                "shift": shift_data
            }
        except Exception as e:
            print(f"[mobile_auth] Error building employee profile: {e}")
            profile_data = {
                "id": str(employee.id),
                "employeeCode": f"EMP{employee.id}",
                "department": None,
                "shiftId": None,
                "isTrackingEnabled": False,
                "shift": None
            }

    # Resolve subscription_enabled for the returned dictionary
    subscription_enabled = False
    if employee:
        company = employee.get_company()
        if company and hasattr(company, 'subscription'):
            subscription_enabled = company.subscription.has_feature("live_location")
    else:
        try:
            work_info = EmployeeWorkInformation.objects.filter(employee_id__employee_user_id=user).first()
            if work_info and work_info.company_id:
                company = work_info.company_id
                if hasattr(company, 'subscription'):
                    subscription_enabled = company.subscription.has_feature("live_location")
            else:
                from base.models import Company
                company = Company.objects.first()
                if company and hasattr(company, 'subscription'):
                    subscription_enabled = company.subscription.has_feature("live_location")
        except Exception:
            pass

    # AI assistant availability for the mobile chatbot tab. Mirrors the web
    # gates exactly: platform AISettings toggle + per-role allow + the
    # company plan's "ai_assistant" feature; "execute" mode additionally
    # needs the plan's "ai_execute" feature and the company's action level.
    ai_assistant = {"enabled": False, "modes": []}
    try:
        from subscriptions.models import AISettings
        from subscriptions.ai_assistant import _action_level, _company_of, _role_of

        cfg = AISettings.load()
        ai_role = _role_of(user)
        role_allowed = {
            "employee": cfg.allow_employee,
            "hr": cfg.allow_hr,
            "ceo": cfg.allow_ceo,
        }[ai_role]
        ai_company = _company_of(user)
        subscription = getattr(ai_company, "subscription", None) if ai_company else None
        plan_ok = is_platform_owner(user) or (
            subscription is not None and subscription.has_feature("ai_assistant")
        )
        if cfg.enabled and cfg.api_key and role_allowed and plan_ok:
            modes = ["guidance", "suggest"]
            if (
                ai_role != "employee"
                and ai_company
                and _action_level(ai_company) == "execute"
                and (
                    is_platform_owner(user)
                    or (subscription and subscription.has_feature("ai_execute"))
                )
            ):
                modes.append("execute")
            ai_assistant = {"enabled": True, "role": ai_role, "modes": modes}
    except Exception:
        pass

    # Employee record holds the real name; auth User's first/last are usually
    # blank and username is the email — which then showed as the profile title.
    display_name = ""
    if employee:
        display_name = employee.get_full_name().strip()
    if not display_name:
        display_name = f"{user.first_name} {user.last_name}".strip() or user.username
    return {
        "id": str(user.id),
        "name": display_name,
        "email": user.email,
        "phone": getattr(employee, "phone", None) if employee else None,
        "role": role,
        "status": "active" if user.is_active else "inactive",
        "liveLocationEnabled": subscription_enabled,
        "permissions": {
            "can_approve_leaves": user.has_perm("leave.change_leaverequest"),
            "can_add_holidays": user.has_perm("base.add_holidays"),
            "can_view_reports": user.has_perm("attendance.view_attendance"),
            "can_manage_attendance": user.has_perm("attendance.change_attendance"),
            "can_view_live_map": user.has_perm("geofencing.view_geofencing"),
            "can_manage_selfies": user.has_perm("facedetection.view_facedetection"),
            "can_manage_announcements": (
                is_platform_owner(user)
                or user.has_perm("base.add_announcement")
                or user.has_perm("base.change_announcement")
                or user.has_perm("base.delete_announcement")
            ),
        },
        "aiAssistant": ai_assistant,
        "employeeProfile": profile_data
    }


class MobileLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({
                "success": False,
                "message": "Email and password are required",
                "errorCode": "MISSING_FIELDS"
            }, status=400)

        # Authenticate using username or email
        user = authenticate(username=email.strip(), password=password)
        if not user:
            # Fallback to authenticating by email field directly
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = User.objects.filter(email__iexact=email.strip()).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if not user:
            return Response({
                "success": False,
                "message": "Invalid email or password",
                "errorCode": "INVALID_CREDENTIALS"
            }, status=401)

        if not user.is_active:
            return Response({
                "success": False,
                "message": "Your account is deactivated",
                "errorCode": "ACCOUNT_INACTIVE"
            }, status=403)

        # This request has no Bearer token yet, so CompanyScopedJWTAuthentication
        # never runs and the tenant context is unset - SkylinxCompanyManager would
        # then return an empty queryset for a scoped (non-owner) user, silently
        # dropping data like the shift's configured working days. Resolve the
        # company here the same way that auth class does for later requests.
        try:
            if is_platform_owner(user):
                set_selected_company("all")
            else:
                set_selected_company(
                    user.employee_get.employee_work_info.company_id_id
                )
        except Exception:
            pass

        refresh = RefreshToken.for_user(user)
        user_data = get_mobile_user_data(user)

        return Response({
            "success": True,
            "message": "Login successful",
            "data": {
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
                "user": user_data
            }
        }, status=200)


class MobileProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_data = get_mobile_user_data(request.user)
        return Response({
            "success": True,
            "message": "Profile loaded",
            "data": user_data
        }, status=200)


class MobileAIChatAPIView(APIView):
    """JWT front door for the AI assistant chat.

    Delegates to the SAME subscriptions.ai_assistant.ai_chat view the web
    widget uses — no duplicated role/plan/PII logic here. We only propagate
    the JWT-authenticated user onto the underlying Django request (DRF keeps
    it on its own wrapper) so @login_required inside ai_chat passes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from subscriptions.ai_assistant import ai_chat

        django_request = request._request
        django_request.user = request.user
        # NOTE: don't touch request.data before this — ai_chat reads the raw
        # request.body itself.
        return ai_chat(django_request)


class MobilePasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        old_password = request.data.get("oldPassword")
        new_password = request.data.get("newPassword")

        if not old_password or not new_password:
            return Response({
                "success": False,
                "message": "Current and new passwords are required",
                "errorCode": "MISSING_FIELDS"
            }, status=400)

        user = request.user
        if not user.check_password(old_password):
            return Response({
                "success": False,
                "message": "Current password is incorrect",
                "errorCode": "INCORRECT_PASSWORD"
            }, status=400)

        user.set_password(new_password)
        user.save()

        return Response({
            "success": True,
            "message": "Password updated successfully",
            "data": {"message": "Password updated successfully"}
        }, status=200)
