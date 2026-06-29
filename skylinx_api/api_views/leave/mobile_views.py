from django.utils import timezone
from base.rbac import is_platform_owner
from datetime import datetime
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from leave.models import LeaveRequest, LeaveType, AvailableLeave, Holiday
from base.models import Holidays


class MobileLeaveApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "errorCode": "NOT_AN_EMPLOYEE"
            }, status=400)

        # Accept both camelCase (default) and snake_case field names; under
        # multipart uploads Flutter may send either.
        leave_type_id    = request.data.get("leaveTypeId") or request.data.get("leave_type_id")
        leave_type_name  = request.data.get("leaveType") or request.data.get("leave_type")
        start_date_str   = request.data.get("startDate") or request.data.get("start_date")
        start_date_breakdown = request.data.get("startDateBreakdown") or request.data.get("start_date_breakdown") or "full_day"
        end_date_str     = request.data.get("endDate") or request.data.get("end_date")
        end_date_breakdown   = request.data.get("endDateBreakdown") or request.data.get("end_date_breakdown") or "full_day"
        reason           = request.data.get("reason", "")
        attachment_file  = request.FILES.get("attachment")

        # ── Required field check ──────────────────────────────────────────────
        if not (leave_type_id or leave_type_name) or not start_date_str or not end_date_str:
            return Response({
                "success": False,
                "message": "leaveTypeId, startDate, and endDate are required",
                "errorCode": "MISSING_FIELDS"
            }, status=400)

        # ── Date parsing ──────────────────────────────────────────────────────
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date   = datetime.strptime(end_date_str,   "%Y-%m-%d").date()
        except ValueError:
            return Response({
                "success": False,
                "message": "Invalid date format. Use YYYY-MM-DD",
                "errorCode": "INVALID_DATE"
            }, status=400)

        if start_date > end_date:
            return Response({
                "success": False,
                "message": "Start date must be on or before end date",
                "errorCode": "INVALID_DATE_RANGE"
            }, status=400)

        # ── Leave type lookup ─────────────────────────────────────────────────
        leave_type = None
        if leave_type_id:
            try:
                leave_type = LeaveType.objects.filter(id=int(leave_type_id)).first()
            except (ValueError, TypeError):
                leave_type = LeaveType.objects.filter(id=leave_type_id).first()
        if not leave_type and leave_type_name:
            leave_type = LeaveType.objects.filter(name__icontains=leave_type_name).first()

        if not leave_type:
            return Response({
                "success": False,
                "message": "Selected leave type was not found",
                "errorCode": "LEAVE_TYPE_NOT_FOUND"
            }, status=400)

        # ── Assignment check (mirrors web form queryset restriction) ─────────
        try:
            available_leave = AvailableLeave.objects.get(
                employee_id=employee, leave_type_id=leave_type
            )
        except AvailableLeave.DoesNotExist:
            return Response({
                "success": False,
                "message": "This leave type is not assigned to you",
                "errorCode": "LEAVE_TYPE_NOT_ASSIGNED"
            }, status=403)

        # ── Attachment requirement check ──────────────────────────────────────
        if leave_type.require_attachment == "yes" and not attachment_file:
            return Response({
                "success": False,
                "message": "An attachment is required for this leave type",
                "errorCode": "ATTACHMENT_REQUIRED"
            }, status=400)

        # ── Overlap check ─────────────────────────────────────────────────────
        overlapping = LeaveRequest.objects.filter(
            employee_id=employee,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exclude(status__in=["cancelled", "rejected"])

        if overlapping.exists():
            return Response({
                "success": False,
                "message": "You already have an approved or pending leave request for these dates",
                "errorCode": "OVERLAPPING_LEAVE"
            }, status=400)

        # ── Balance check ─────────────────────────────────────────────────────
        from leave.methods import calculate_requested_days

        requested_days = calculate_requested_days(
            start_date, end_date, start_date_breakdown, end_date_breakdown
        )

        available_days    = available_leave.available_days or 0
        carryforward_days = available_leave.carryforward_days or 0
        carryforward_type = leave_type.carryforward_type or "no carryforward"
        carryforward_max  = leave_type.carryforward_max or 0

        if carryforward_type in ["carryforward", "carryforward expire"]:
            carryforward_days = min(carryforward_days, carryforward_max)
        elif carryforward_type == "no carryforward":
            carryforward_days = 0

        total_available = available_days + carryforward_days

        if requested_days > total_available:
            return Response({
                "success": False,
                "message": f"Insufficient leave balance. You have {total_available} day(s) available but requested {requested_days}",
                "errorCode": "INSUFFICIENT_BALANCE"
            }, status=400)

        # ── Save ──────────────────────────────────────────────────────────────
        try:
            leave_request = LeaveRequest(
                employee_id=employee,
                leave_type_id=leave_type,
                start_date=start_date,
                start_date_breakdown=start_date_breakdown,
                end_date=end_date,
                end_date_breakdown=end_date_breakdown,
                description=reason,
                attachment=attachment_file,
                status="requested",
                created_by=employee,
            )
            leave_request.requested_days = requested_days
            leave_request.save()
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Failed to save leave request: {str(e)}",
                "errorCode": "SAVE_ERROR"
            }, status=500)

        return Response({
            "success": True,
            "message": "Leave request submitted successfully",
            "data": {
                "id": str(leave_request.id),
                "status": leave_request.status,
                "requestedDays": leave_request.requested_days,
                "leaveType": leave_type.name,
                "startDate": start_date_str,
                "endDate": end_date_str,
            }
        }, status=201)



class MobileMyLeavesAPIView(APIView):
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

        # Fetch leave requests
        year_str = request.query_params.get("year")
        qs = LeaveRequest.objects.filter(employee_id=employee)

        if year_str:
            try:
                year = int(year_str)
                qs = qs.filter(start_date__year=year)
            except ValueError:
                pass

        qs = qs.order_by("-start_date")
        
        # Serialize list
        leaves = []
        for lr in qs:
            leaves.append({
                "id": str(lr.id),
                "leaveType": lr.leave_type_id.name if lr.leave_type_id else "Leave",
                "startDate": lr.start_date.isoformat(),
                "endDate": lr.end_date.isoformat() if lr.end_date else lr.start_date.isoformat(),
                "totalDays": lr.requested_days or 1.0,
                "reason": lr.description or "",
                "status": lr.status, # matches requested, approved, cancelled, rejected
                "createdAt": lr.created_at.isoformat() if hasattr(lr, "created_at") else lr.requested_date.isoformat()
            })

        return Response({
            "success": True,
            "message": "Leaves retrieved",
            "data": leaves
        }, status=200)


class MobileLeaveSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "data": {}
            }, status=400)

        year = timezone.now().year

        # Aggregate all leave requests for this employee in the current year
        taken_total = LeaveRequest.objects.filter(
            employee_id=employee,
            start_date__year=year,
            status="approved"
        ).aggregate(total=Sum("requested_days"))["total"] or 0.0

        pending_total = LeaveRequest.objects.filter(
            employee_id=employee,
            start_date__year=year,
            status__in=["requested", "pending"]
        ).aggregate(total=Sum("requested_days"))["total"] or 0.0

        # Sick leave taken
        sick_taken = LeaveRequest.objects.filter(
            employee_id=employee,
            start_date__year=year,
            status="approved",
            leave_type_id__name__icontains="sick"
        ).aggregate(total=Sum("requested_days"))["total"] or 0.0

        # LOP taken
        lop_taken = LeaveRequest.objects.filter(
            employee_id=employee,
            start_date__year=year,
            status="approved",
            leave_type_id__name__icontains="lop"
        ).aggregate(total=Sum("requested_days"))["total"] or 0.0

        return Response({
            "success": True,
            "message": "Leave summary loaded",
            "data": {
                "year": year,
                "sick": sick_taken,
                "lop": lop_taken,
                "total": taken_total,
                "pending": pending_total,
            }
        }, status=200)


class MobileLeaveCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({
                "success": False,
                "message": "User is not registered as an employee",
                "errorCode": "NOT_AN_EMPLOYEE"
            }, status=400)

        lr = LeaveRequest.objects.filter(id=pk, employee_id=employee).first()
        if not lr:
            return Response({
                "success": False,
                "message": "Leave request not found",
                "errorCode": "NOT_FOUND"
            }, status=404)

        if lr.status in ["approved", "rejected"]:
            return Response({
                "success": False,
                "message": f"Cannot cancel leave request that is already {lr.status}",
                "errorCode": "INVALID_STATE"
            }, status=400)

        lr.status = "cancelled"
        lr.save()

        return Response({
            "success": True,
            "message": "Leave request cancelled successfully",
            "data": {
                "id": str(lr.id),
                "status": lr.status
            }
        }, status=200)


from base.models import Holidays, Company


class MobileHolidaysAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date, timedelta
        import calendar
        from django.db.models import Q

        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except (ValueError, TypeError):
            year = today.year
            month = today.month

        if not (1 <= month <= 12):
            month = today.month
        if year < 1970 or year > 2100:
            year = today.year

        _, num_days = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, num_days)

        # Resolve the selected company so we can include global (company_id NULL)
        # holidays without leaking other tenants' data. The default scoped manager
        # filters on strict company_id equality, which silently drops globals.
        from skylinx.skylinx_middlewares import get_selected_company
        company = get_selected_company()
        if company == "all":
            company_filter = Q()  # platform owner: all tenants
        elif company:
            company_filter = Q(company_id=company) | Q(company_id__isnull=True)
        else:
            company_filter = Q(company_id__isnull=True)  # no tenant leak: globals only

        overlap_filter = (
            (Q(start_date__lte=month_end) & Q(end_date__gte=month_start)) |
            (Q(end_date__isnull=True) & Q(start_date__lte=month_end) & Q(start_date__gte=month_start))
        )

        # 1. Fetch holidays from leave.Holiday overlapping this month (incl. globals)
        qs1 = Holiday.objects.entire().filter(company_filter).filter(
            overlap_filter
        ).order_by("start_date")

        # 2. Fetch holidays from base.Holidays overlapping this month (incl. globals)
        qs2 = Holidays.objects.entire().filter(company_filter).filter(
            overlap_filter
        ).order_by("start_date")

        holidays_list = []
        for h in qs1:
            holidays_list.append({
                "id": f"leave_{h.id}",
                "name": h.name,
                "startDate": h.start_date.isoformat(),
                "endDate": (h.end_date or h.start_date).isoformat(),
                "description": getattr(h, "description", "") or "",
                "isOptional": False
            })

        for h in qs2:
            holidays_list.append({
                "id": f"base_{h.id}",
                "name": h.name,
                "startDate": h.start_date.isoformat(),
                "endDate": (h.end_date or h.start_date).isoformat(),
                "description": getattr(h, "description", "") or "",
                "isOptional": getattr(h, "is_optional", False)
            })

        # Fetch approved leaves overlapping this month
        leaves_qs = LeaveRequest.objects.filter(
            status="approved",
            start_date__lte=month_end,
            end_date__gte=month_start
        )

        is_admin = is_platform_owner(request.user) or request.user.groups.filter(name="Admin").exists() or request.user.has_perm("employee.change_employee") or request.user.has_perm("employee.add_employee")
        if not is_admin:
            leaves_qs = leaves_qs.none()

        leaves_qs = leaves_qs.select_related("employee_id", "leave_type_id").order_by("start_date")

        leaves_list = []
        for l in leaves_qs:
            leaves_list.append({
                "id": str(l.id),
                "employeeName": l.employee_id.get_full_name() if l.employee_id else "Employee",
                "leaveType": l.leave_type_id.name if l.leave_type_id else "Leave",
                "startDate": l.start_date.isoformat(),
                "endDate": l.end_date.isoformat() if l.end_date else l.start_date.isoformat(),
                "totalDays": float(l.requested_days or 1.0)
            })

        # Dynamic weekend (off-day) mapping from CompanyLeaves, matching the web
        # holiday calendar. Python weekday 0-6 -> Dart/ISO 1-7. Default Sat/Sun.
        from base.models import CompanyLeaves
        company_leaves = CompanyLeaves.objects.entire().filter(company_filter)
        weekends = []
        for cl in company_leaves:
            try:
                val = int(cl.based_on_week_day) + 1
                if val not in weekends:
                    weekends.append(val)
            except (ValueError, TypeError):
                pass
        if not weekends:
            weekends = [6, 7]

        # Exact calendar dates of company off-days this month (supports rules
        # like "2nd Saturday"), so the app can shade them precisely.
        company_leave_dates = []
        if company_leaves.exists():
            try:
                from leave.methods import company_leave_dates_list
                for dt in company_leave_dates_list(company_leaves, month_start):
                    if dt.month == month and dt.year == year:
                        company_leave_dates.append(dt.isoformat())
            except Exception:
                pass

        return Response({
            "success": True,
            "message": "Holidays and leaves loaded",
            "data": {
                "year": year,
                "month": month,
                "monthName": calendar.month_name[month],
                "holidays": holidays_list,
                "leaves": leaves_list,
                "weekends": weekends,
                "companyLeaves": company_leave_dates,
            }
        }, status=200)

    def post(self, request):
        if not (is_platform_owner(request.user) or request.user.groups.filter(name="Admin").exists()):
            return Response({
                "success": False,
                "message": "Only admins can create holidays"
            }, status=403)

        name = request.data.get("name")
        date_str = request.data.get("date")
        is_optional = request.data.get("isOptional", False)

        if isinstance(is_optional, str):
            is_optional = is_optional.lower() == "true"
        else:
            is_optional = bool(is_optional)

        if not name or not date_str:
            return Response({
                "success": False,
                "message": "name and date are required"
            }, status=400)

        try:
            date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({
                "success": False,
                "message": "Invalid date format. Use YYYY-MM-DD"
            }, status=400)

        company = None
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            pass

        holiday = Holidays.objects.create(
            name=name,
            start_date=date_val,
            end_date=date_val,
            is_optional=is_optional,
            company_id=company,
            created_by=request.user
        )

        return Response({
            "success": True,
            "message": "Holiday created successfully",
            "data": {
                "id": f"base_{holiday.id}",
                "name": holiday.name,
                "startDate": holiday.start_date.isoformat(),
                "endDate": holiday.end_date.isoformat() if holiday.end_date else holiday.start_date.isoformat(),
                "isOptional": holiday.is_optional
            }
        }, status=201)


class MobileAdminLeaveListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (is_platform_owner(request.user) or request.user.groups.filter(name="Admin").exists()):
            return Response({
                "success": False,
                "message": "Only admins can view leave list",
                "data": []
            }, status=403)

        status_filter = request.query_params.get("status", "all")
        user_id = request.query_params.get("userId")

        qs = LeaveRequest.objects.all()

        if status_filter == "pending":
            qs = qs.filter(status="requested")
        elif status_filter in ["approved", "rejected", "cancelled"]:
            qs = qs.filter(status=status_filter)
        
        if user_id:
            qs = qs.filter(employee_id__employee_user_id_id=user_id)

        qs = qs.select_related("employee_id", "employee_id__employee_user_id", "leave_type_id").order_by("-id")

        leaves = []
        for lr in qs:
            emp = lr.employee_id
            emp_user = emp.employee_user_id if emp else None
            
            # Map requested to pending for the mobile admin UI
            mapped_status = "pending" if lr.status == "requested" else lr.status

            dept_name = ""
            try:
                work_info = getattr(emp, "employee_work_info", None)
                if work_info and work_info.department_id:
                    dept_name = str(work_info.department_id.department)
            except Exception:
                pass

            leaves.append({
                "id": str(lr.id),
                "leaveType": lr.leave_type_id.name if lr.leave_type_id else "Leave",
                "startDate": lr.start_date.isoformat(),
                "endDate": lr.end_date.isoformat() if lr.end_date else lr.start_date.isoformat(),
                "totalDays": int(lr.requested_days or 1.0),
                "reason": lr.description or "",
                "status": mapped_status,
                "reviewNote": lr.reject_reason or "",
                "user": {
                    "id": str(emp_user.id) if emp_user else "",
                    "name": emp.get_full_name() if emp else "Unknown",
                    "employeeProfile": {
                        "employeeCode": emp.badge_id if (emp and emp.badge_id) else (f"EMP{emp.id}" if emp else ""),
                        "department": dept_name
                    }
                }
            })

        return Response({
            "success": True,
            "message": "Leaves retrieved for admin",
            "data": leaves
        }, status=200)


class MobileAdminLeaveReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not (is_platform_owner(request.user) or request.user.groups.filter(name="Admin").exists()):
            return Response({
                "success": False,
                "message": "Only admins can review leave requests"
            }, status=403)

        try:
            leave_request = LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({
                "success": False,
                "message": "Leave request not found"
            }, status=404)

        action = request.data.get("action") # approved, rejected
        review_note = request.data.get("reviewNote", "")

        if action not in ["approved", "rejected"]:
            return Response({
                "success": False,
                "message": "Action must be either approved or rejected"
            }, status=400)

        employee = leave_request.employee_id
        leave_type = leave_request.leave_type_id

        # Get or create AvailableLeave if not exists
        available_leave, created = AvailableLeave.objects.get_or_create(
            leave_type_id=leave_type,
            employee_id=employee,
            defaults={"available_days": 10.0, "carryforward_days": 0.0}
        )

        if action == "approved":
            if leave_request.status == "approved":
                return Response({"success": True, "message": "Already approved"}, status=200)

            total_available = available_leave.available_days + available_leave.carryforward_days
            if total_available < leave_request.requested_days:
                return Response({
                    "success": False,
                    "message": f"Employee does not have enough leave days ({total_available} available, {leave_request.requested_days} requested)."
                }, status=400)

            # Approve calculation
            if leave_request.requested_days > available_leave.available_days:
                rem = leave_request.requested_days - available_leave.available_days
                leave_request.approved_available_days = available_leave.available_days
                available_leave.available_days = 0
                available_leave.carryforward_days = available_leave.carryforward_days - rem
                leave_request.approved_carryforward_days = rem
            else:
                available_leave.available_days -= leave_request.requested_days
                leave_request.approved_available_days = leave_request.requested_days
                leave_request.approved_carryforward_days = 0

            available_leave.save()
            leave_request.status = "approved"
            leave_request.save()
        else: # rejected
            # If previously approved, restore days
            if leave_request.status == "approved":
                available_leave.available_days += leave_request.approved_available_days
                available_leave.carryforward_days += leave_request.approved_carryforward_days
                available_leave.save()

            leave_request.approved_available_days = 0
            leave_request.approved_carryforward_days = 0
            leave_request.status = "rejected"
            leave_request.reject_reason = review_note
            leave_request.save()

        return Response({
            "success": True,
            "message": f"Leave request {action} successfully",
            "data": {
                "id": str(leave_request.id),
                "status": "approved" if action == "approved" else "rejected"
            }
        }, status=200)


class MobileAdminHolidayDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not (is_platform_owner(request.user) or request.user.groups.filter(name="Admin").exists()):
            return Response({
                "success": False,
                "message": "Only admins can delete holidays"
            }, status=403)

        if pk.startswith("leave_"):
            db_id = pk.replace("leave_", "")
            try:
                holiday = Holiday.objects.get(id=db_id)
                holiday.delete()
            except Holiday.DoesNotExist:
                return Response({"success": False, "message": "Holiday not found"}, status=404)
        elif pk.startswith("base_"):
            db_id = pk.replace("base_", "")
            try:
                holiday = Holidays.objects.get(id=db_id)
                holiday.delete()
            except Holidays.DoesNotExist:
                return Response({"success": False, "message": "Holiday not found"}, status=404)
        else:
            try:
                holiday = Holiday.objects.get(id=pk)
                holiday.delete()
            except Exception:
                try:
                    holiday = Holidays.objects.get(id=pk)
                    holiday.delete()
                except Exception:
                    return Response({"success": False, "message": "Holiday not found"}, status=404)

        return Response({"success": True, "message": "Holiday deleted successfully"}, status=200)


class MobileAvailableLeaveTypesAPIView(APIView):
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

        # Mirror the web form's logic exactly (leave/forms.py LeaveRequestUpdationForm):
        # use employee.available_leave.all() — no is_active filter — so every leave
        # type that has been assigned to this employee appears in the dropdown.
        available_leaves = employee.available_leave.all().select_related("leave_type_id")

        data = []
        for al in available_leaves:
            lt = al.leave_type_id
            if lt is None:
                continue
            total_days = al.available_days + al.carryforward_days
            data.append({
                "id": str(lt.id),
                "name": lt.name,
                # Days remaining in the regular allocation bucket
                "availableDays": float(al.available_days),
                # Carry-forward bucket (shown separately so UI can display it)
                "carryforwardDays": float(al.carryforward_days),
                # Combined total for quick display
                "totalDays": float(total_days),
                "requireAttachment": lt.require_attachment == "yes",
                # Whether this leave type is paid
                "isPaid": lt.payment == "paid",
                # Payment type label
                "paymentType": lt.payment_type or lt.payment or "unpaid",
            })

        return Response({
            "success": True,
            "message": "Available leave types retrieved",
            "data": data
        }, status=200)
