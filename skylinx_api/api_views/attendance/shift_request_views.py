"""
skylinx_api/api_views/attendance/shift_request_views.py

Mobile API views for employee shift change requests.
Uses base.models.ShiftRequest — the existing model in the Skylinx schema.

Endpoints (all under /api/v1/attendance/):
  GET  /shifts/                       → list all available shifts for the company
  GET  /shift-requests/               → list employee's own shift requests
  POST /shift-requests/               → create a new shift request
  PATCH /shift-requests/<pk>/cancel/  → cancel a pending shift request
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.models import EmployeeShift, ShiftRequest


class MobileShiftListAPIView(APIView):
    """Return all available shifts the employee can select when making a shift request."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            return Response({"success": False, "message": "Employee not found."}, status=400)

        qs = EmployeeShift.objects.all()
        if company:
            qs = qs.filter(company_id=company)

        shifts = []
        for s in qs:
            shifts.append({
                "id": str(s.id),
                "name": s.employee_shift,
                "weeklyFullTime": s.weekly_full_time,
                "fullTime": s.full_time,
            })

        return Response({"success": True, "data": shifts}, status=200)


class MobileShiftRequestAPIView(APIView):
    """
    GET  – list the authenticated employee's own shift requests.
    POST – submit a new shift change request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Employee not found."}, status=400)

        qs = ShiftRequest.objects.filter(employee_id=employee).select_related(
            "shift_id", "previous_shift_id"
        ).order_by("-created_at")

        results = []
        for r in qs:
            # Determine status string from boolean flags
            if r.reallocate_canceled or r.canceled:
                status = "cancelled"
            elif r.reallocate_approved or r.approved:
                status = "approved"
            else:
                status = "requested"

            results.append({
                "id": str(r.id),
                "requestedShiftId": str(r.shift_id.id) if r.shift_id else None,
                "requestedShiftName": r.shift_id.employee_shift if r.shift_id else "",
                "previousShiftId": str(r.previous_shift_id.id) if r.previous_shift_id else None,
                "previousShiftName": r.previous_shift_id.employee_shift if r.previous_shift_id else None,
                "requestedDate": r.requested_date.isoformat() if r.requested_date else None,
                "requestedTill": r.requested_till.isoformat() if r.requested_till else None,
                "reason": r.description or "",
                "isPermanent": r.is_permanent_shift,
                "status": status,
                "approved": r.approved,
                "canceled": r.canceled or r.reallocate_canceled,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            })

        return Response({"success": True, "data": results}, status=200)

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Employee not found."}, status=400)

        requested_shift_id = request.data.get("requestedShiftId")
        requested_date = request.data.get("requestedDate")
        requested_till = request.data.get("requestedTill")  # optional
        reason = request.data.get("reason", "")
        is_permanent = request.data.get("isPermanent", False)

        if not requested_shift_id or not requested_date:
            return Response(
                {"success": False, "message": "requestedShiftId and requestedDate are required."},
                status=400,
            )

        # Validate the requested shift exists
        try:
            requested_shift = EmployeeShift.objects.get(id=requested_shift_id)
        except EmployeeShift.DoesNotExist:
            return Response({"success": False, "message": "Shift not found."}, status=404)

        # Capture the employee's current shift as previous_shift
        previous_shift = None
        try:
            work_info = employee.employee_work_info
            previous_shift = work_info.shift_id
        except Exception:
            pass

        # Prevent requesting the same shift
        if previous_shift and previous_shift.id == requested_shift.id:
            return Response(
                {"success": False, "message": "You are already assigned to this shift."},
                status=400,
            )

        shift_request = ShiftRequest.objects.create(
            employee_id=employee,
            shift_id=requested_shift,
            previous_shift_id=previous_shift,
            requested_date=requested_date,
            requested_till=requested_till or None,
            description=reason,
            is_permanent_shift=bool(is_permanent),
            approved=False,
            canceled=False,
            shift_changed=False,
        )

        return Response({
            "success": True,
            "message": "Shift change request submitted successfully.",
            "data": {
                "id": str(shift_request.id),
                "requestedShiftName": requested_shift.employee_shift,
                "requestedDate": requested_date,
                "status": "requested",
            },
        }, status=201)


class MobileShiftRequestCancelAPIView(APIView):
    """Allow employee to cancel their own pending shift request."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Employee not found."}, status=400)

        try:
            shift_request = ShiftRequest.objects.get(id=pk, employee_id=employee)
        except ShiftRequest.DoesNotExist:
            return Response({"success": False, "message": "Shift request not found."}, status=404)

        # Cannot cancel an already approved or canceled request
        if shift_request.approved:
            return Response(
                {"success": False, "message": "Cannot cancel an already approved request."},
                status=400,
            )
        if shift_request.canceled or shift_request.reallocate_canceled:
            return Response(
                {"success": False, "message": "This request is already cancelled."},
                status=400,
            )

        shift_request.canceled = True
        shift_request.save()

        return Response({
            "success": True,
            "message": "Shift request cancelled.",
            "data": {"id": str(shift_request.id), "status": "cancelled"},
        }, status=200)
