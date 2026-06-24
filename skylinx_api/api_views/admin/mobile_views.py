import os
import json
import csv
import math
from datetime import datetime, date, timedelta

from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from attendance.models import Attendance, AttendanceActivity, MobileAttendanceDetail, MobileLocationLog
from employee.models import Employee
from notifications.models import Notification
from geofencing.models import GeoFencing
from facedetection.models import FaceDetection
from geopy.distance import geodesic

def get_company_settings(company):
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
        
        fd = FaceDetection.objects.filter(company_id=company).first()
        if fd:
            face_enabled = fd.start
            
    # Load extra mobile settings from JSON file
    tracking_enabled = True
    reminder_enabled = True
    missed_selfie_threshold = 15
    
    settings_dir = os.path.join(settings.MEDIA_ROOT, "company_settings")
    os.makedirs(settings_dir, exist_ok=True)
    settings_path = os.path.join(settings_dir, f"settings_{company.id if company else 0}.json")
    
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r") as f:
                data = json.load(f)
                tracking_enabled = data.get("trackingEnabled", True)
                reminder_enabled = data.get("reminderEnabled", True)
                missed_selfie_threshold = data.get("missedSelfieThresholdMinutes", 15)
        except Exception:
            pass
            
    return {
        "id": str(company.id if company else 0),
        "geofenceRadiusMeters": geofence_radius,
        "reminderEnabled": reminder_enabled,
        "missedSelfieThresholdMinutes": missed_selfie_threshold,
        "trackingEnabled": tracking_enabled,
        "officeLat": office_lat,
        "officeLng": office_lng,
        "officeAddress": office_address,
        "faceEnabled": face_enabled,
        "geofenceEnabled": geofence_enabled
    }

class MobileAdminAttendanceSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
            
        total_employees = Employee.objects.filter(is_active=True).count()
        present = AttendanceActivity.objects.filter(attendance_date=target_date).values('employee_id').distinct().count()
        absent = max(0, total_employees - present)
        
        checked_out = AttendanceActivity.objects.filter(
            attendance_date=target_date,
            out_datetime__isnull=False
        ).values('employee_id').distinct().count()
        
        activities = AttendanceActivity.objects.filter(attendance_date=target_date)
        missed_selfie = 0
        for act in activities:
            detail = getattr(act, 'mobile_detail', None)
            if not detail or not detail.check_in_selfie:
                missed_selfie += 1
                
        gps_off = MobileLocationLog.objects.filter(
            captured_at__date=target_date,
            gps_enabled=False
        ).values('employee_id').distinct().count()
        
        outside_geofence = MobileAttendanceDetail.objects.filter(
            attendance_activity__attendance_date=target_date
        ).filter(models.Q(within_geofence=False) | models.Q(check_out_within_geofence=False)).values('attendance_activity__employee_id').distinct().count()
        
        return Response({
            "success": True,
            "data": {
                "date": target_date.strftime("%Y-%m-%d"),
                "totalEmployees": total_employees,
                "present": present,
                "absent": absent,
                "checkedOut": checked_out,
                "missedSelfie": missed_selfie,
                "gpsOff": gps_off,
                "outsideGeofence": outside_geofence
            }
        }, status=200)

class MobileAdminAlertsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        unread_only = request.query_params.get("unreadOnly", "false").lower() == "true"
        
        notifications = Notification.objects.filter(recipient=request.user)
        if unread_only:
            notifications = notifications.filter(unread=True)
            
        alerts_list = []
        for n in notifications.order_by("-timestamp"):
            actor_data = None
            if n.actor:
                try:
                    actor_data = {
                        "id": str(n.actor_object_id),
                        "name": f"{n.actor.first_name} {n.actor.last_name}".strip() or n.actor.username
                    }
                except Exception:
                    actor_data = {
                        "id": str(n.actor_object_id),
                        "name": str(n.actor)
                    }
            
            verb_lower = n.verb.lower()
            if "gps off" in verb_lower or "turned off gps" in verb_lower:
                alert_type = "gps_off"
            elif "outside geofence" in verb_lower or "geofence" in verb_lower:
                alert_type = "check_in"
            elif "missed selfie" in verb_lower:
                alert_type = "missed_selfie"
            else:
                alert_type = "notification"
                
            alerts_list.append({
                "id": str(n.id),
                "actorUserId": str(n.actor_object_id) if n.actor else None,
                "alertType": alert_type,
                "title": n.verb,
                "message": n.description or n.verb,
                "isRead": not n.unread,
                "createdAt": n.timestamp.isoformat(),
                "actor": actor_data
            })
            
        return Response({
            "success": True,
            "data": alerts_list
        }, status=200)

class MobileAdminMarkAlertReadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, pk):
        try:
            n = Notification.objects.get(id=pk, recipient=request.user)
            n.mark_as_read()
            return Response({"success": True, "message": "Alert marked as read"})
        except Notification.DoesNotExist:
            return Response({"success": False, "message": "Alert not found"}, status=404)

class MobileAdminMarkAllAlertsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
        return Response({"success": True, "message": "All alerts marked as read"})

class MobileAdminSelfieFeedAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_str = request.query_params.get("date")
        user_id = request.query_params.get("userId")
        within_geofence_str = request.query_params.get("withinGeofence")
        
        activities = AttendanceActivity.objects.filter(
            models.Q(mobile_detail__check_in_selfie__isnull=False) |
            models.Q(mobile_detail__check_out_selfie__isnull=False)
        )
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                activities = activities.filter(attendance_date=target_date)
            except ValueError:
                pass
                
        if user_id:
            activities = activities.filter(employee_id__employee_user_id__id=user_id)
            
        if within_geofence_str:
            within_geofence = within_geofence_str.lower() == "true"
            activities = activities.filter(
                models.Q(mobile_detail__within_geofence=within_geofence) |
                models.Q(mobile_detail__check_out_within_geofence=within_geofence)
            )
            
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        start = (page - 1) * limit
        end = page * limit
        
        total = activities.count()
        activities_slice = activities.order_by("-attendance_date", "-clock_in")[start:end]
        
        events = []
        for act in activities_slice:
            detail = getattr(act, "mobile_detail", None)
            if not detail:
                continue
                
            emp = act.employee_id
            user = emp.employee_user_id
            if not user:
                continue
                
            user_data = {
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "employeeProfile": {
                    "employeeCode": emp.badge_id or f"EMP{emp.id}",
                    "department": str(emp.employee_work_info.department_id.department) if hasattr(emp, 'employee_work_info') and emp.employee_work_info.department_id else None
                }
            }
            
            # Check In Selfie
            if detail.check_in_selfie:
                if within_geofence_str is None or (within_geofence_str.lower() == "true" and detail.within_geofence) or (within_geofence_str.lower() == "false" and not detail.within_geofence):
                    events.append({
                        "id": f"{act.id}_in",
                        "userId": str(user.id),
                        "eventType": "check_in",
                        "selfieUrl": request.build_absolute_uri(detail.check_in_selfie.url),
                        "withinGeofence": detail.within_geofence,
                        "createdAt": act.in_datetime.isoformat() if act.in_datetime else act.created_at.isoformat(),
                        "user": user_data
                    })
                
            # Check Out Selfie
            if detail.check_out_selfie:
                if within_geofence_str is None or (within_geofence_str.lower() == "true" and detail.check_out_within_geofence) or (within_geofence_str.lower() == "false" and not detail.check_out_within_geofence):
                    events.append({
                        "id": f"{act.id}_out",
                        "userId": str(user.id),
                        "eventType": "check_out",
                        "selfieUrl": request.build_absolute_uri(detail.check_out_selfie.url),
                        "withinGeofence": detail.check_out_within_geofence,
                        "createdAt": act.out_datetime.isoformat() if act.out_datetime else act.created_at.isoformat(),
                        "user": user_data
                    })
                    
        pages = math.ceil(total / limit)
        
        return Response({
            "success": True,
            "data": {
                "data": events,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": pages
                }
            }
        }, status=200)

class MobileAdminLocationMapAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            from base.models import Company
            company = Company.objects.first()
            
        gf = GeoFencing.objects.filter(company_id=company).first()
        office_lat = gf.latitude if gf else None
        office_lng = gf.longitude if gf else None
        geofence_radius = gf.radius_in_meters if gf else 100
        
        active_employees = Employee.objects.filter(is_active=True)
        if company:
            active_employees = active_employees.filter(employee_work_info__company_id=company)
            
        logs_list = []
        for emp in active_employees:
            user = emp.employee_user_id
            if not user:
                continue
                
            checked_in = AttendanceActivity.objects.filter(
                employee_id=emp,
                attendance_date=date.today()
            ).exists()
            
            if not checked_in:
                continue
                
            latest_log = MobileLocationLog.objects.filter(employee=emp).order_by("-captured_at").first()
            if not latest_log:
                continue
                
            within_gf = True
            if gf:
                try:
                    distance = geodesic((gf.latitude, gf.longitude), (latest_log.latitude, latest_log.longitude)).meters
                    if distance > gf.radius_in_meters:
                        within_gf = False
                except Exception:
                    pass
                    
            logs_list.append({
                "userId": str(user.id),
                "name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "employeeCode": emp.badge_id or f"EMP{emp.id}",
                "department": str(emp.employee_work_info.department_id.department) if hasattr(emp, 'employee_work_info') and emp.employee_work_info.department_id else None,
                "latitude": latest_log.latitude,
                "longitude": latest_log.longitude,
                "accuracy": latest_log.accuracy or 0.0,
                "gpsEnabled": latest_log.gps_enabled,
                "capturedAt": latest_log.captured_at.isoformat(),
                "withinGeofence": within_gf
            })
            
        return Response({
            "success": True,
            "data": {
                "officeLat": office_lat,
                "officeLng": office_lng,
                "geofenceRadius": geofence_radius,
                "employees": logs_list
            }
        }, status=200)

class MobileAdminDailyReportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
            
        activities = AttendanceActivity.objects.filter(attendance_date=target_date)
        
        events = []
        check_ins = 0
        check_outs = 0
        missed_selfies = 0
        outside_geofence = 0
        
        for act in activities:
            detail = getattr(act, "mobile_detail", None)
            emp = act.employee_id
            user = emp.employee_user_id
            if not user:
                continue
                
            user_data = {
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "employeeProfile": {
                    "employeeCode": emp.badge_id or f"EMP{emp.id}",
                    "department": str(emp.employee_work_info.department_id.department) if hasattr(emp, 'employee_work_info') and emp.employee_work_info.department_id else None
                }
            }
            
            # Check In Event
            if act.in_datetime:
                check_ins += 1
                selfie_url = request.build_absolute_uri(detail.check_in_selfie.url) if (detail and detail.check_in_selfie) else None
                within_gf = detail.within_geofence if detail else True
                
                if detail and not detail.check_in_selfie:
                    missed_selfies += 1
                if detail and not detail.within_geofence:
                    outside_geofence += 1
                    
                events.append({
                    "id": f"{act.id}_in",
                    "userId": str(user.id),
                    "eventType": "check_in",
                    "selfieUrl": selfie_url,
                    "withinGeofence": within_gf,
                    "distanceFromCenterMeters": 0.0,
                    "gpsEnabled": True,
                    "createdAt": act.in_datetime.isoformat() if act.in_datetime else act.created_at.isoformat(),
                    "user": user_data
                })
                
            # Check Out Event
            if act.out_datetime:
                check_outs += 1
                selfie_url = request.build_absolute_uri(detail.check_out_selfie.url) if (detail and detail.check_out_selfie) else None
                within_gf = detail.check_out_within_geofence if detail else True
                
                if detail and not detail.check_out_selfie:
                    missed_selfies += 1
                if detail and not detail.check_out_within_geofence:
                    outside_geofence += 1
                    
                events.append({
                    "id": f"{act.id}_out",
                    "userId": str(user.id),
                    "eventType": "check_out",
                    "selfieUrl": selfie_url,
                    "withinGeofence": within_gf,
                    "distanceFromCenterMeters": 0.0,
                    "gpsEnabled": True,
                    "createdAt": act.out_datetime.isoformat() if act.out_datetime else act.created_at.isoformat(),
                    "user": user_data
                })
                
        gps_off_events = MobileLocationLog.objects.filter(
            captured_at__date=target_date,
            gps_enabled=False
        ).values('employee_id').distinct().count()
        
        return Response({
            "success": True,
            "data": {
                "checkIns": check_ins,
                "checkOuts": check_outs,
                "missedSelfies": missed_selfies,
                "gpsOffEvents": gps_off_events,
                "outsideGeofence": outside_geofence,
                "totalEvents": len(events),
                "events": events
            }
        }, status=200)

class MobileAdminExportCsvAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        start_date_str = request.query_params.get("startDate")
        end_date_str = request.query_params.get("endDate")
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start_date = date.today() - timedelta(days=6)
            end_date = date.today()
            
        activities = AttendanceActivity.objects.filter(
            attendance_date__range=[start_date, end_date]
        ).order_by("attendance_date", "clock_in")
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Employee Code', 'Name', 'Department', 
            'Clock In', 'Clock Out', 'Status', 'Selfie Checked', 'Within Geofence'
        ])
        
        for act in activities:
            detail = getattr(act, "mobile_detail", None)
            emp = act.employee_id
            dept = str(emp.employee_work_info.department_id.department) if hasattr(emp, 'employee_work_info') and emp.employee_work_info.department_id else 'N/A'
            
            in_selfie = "Yes" if (detail and detail.check_in_selfie) else "No"
            in_gf = "Yes" if (detail and detail.within_geofence) else "No"
            
            writer.writerow([
                act.attendance_date.strftime("%Y-%m-%d"),
                emp.badge_id or f"EMP{emp.id}",
                f"{emp.employee_first_name} {emp.employee_last_name}".strip(),
                dept,
                act.clock_in or 'N/A',
                act.clock_out or 'N/A',
                act.attendance_id.attendance_status if act.attendance_id else 'N/A',
                in_selfie,
                in_gf
            ])
            
        return response

class MobileAdminSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            from base.models import Company
            company = Company.objects.first()
            
        settings_data = get_company_settings(company)
        return Response({
            "success": True,
            "data": settings_data
        }, status=200)
        
    def put(self, request):
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            from base.models import Company
            company = Company.objects.first()
            
        payload = request.data
        
        if company:
            gf, created = GeoFencing.objects.get_or_create(
                company_id=company, 
                defaults={"latitude": 0.0, "longitude": 0.0, "radius_in_meters": 100}
            )
            if "geofenceRadiusMeters" in payload:
                gf.radius_in_meters = int(payload["geofenceRadiusMeters"])
            if "officeLat" in payload:
                gf.latitude = float(payload["officeLat"])
            if "officeLng" in payload:
                gf.longitude = float(payload["officeLng"])
            if "geofenceEnabled" in payload:
                gf.start = bool(payload["geofenceEnabled"])
            gf.save()
            
            if "officeAddress" in payload and payload["officeAddress"]:
                company.address = payload["officeAddress"]
                company.save()
                
            if "faceEnabled" in payload:
                fd, _ = FaceDetection.objects.get_or_create(company_id=company)
                fd.start = bool(payload["faceEnabled"])
                fd.save()
                
        # Update extra mobile settings in JSON
        tracking_enabled = payload.get("trackingEnabled", True)
        reminder_enabled = payload.get("reminderEnabled", True)
        missed_selfie_threshold = payload.get("missedSelfieThresholdMinutes", 15)
        
        settings_dir = os.path.join(settings.MEDIA_ROOT, "company_settings")
        os.makedirs(settings_dir, exist_ok=True)
        settings_path = os.path.join(settings_dir, f"settings_{company.id if company else 0}.json")
        
        with open(settings_path, "w") as f:
            json.dump({
                "trackingEnabled": tracking_enabled,
                "reminderEnabled": reminder_enabled,
                "missedSelfieThresholdMinutes": missed_selfie_threshold
            }, f)
            
        settings_data = get_company_settings(company)
        return Response({
            "success": True,
            "data": settings_data
        }, status=200)
