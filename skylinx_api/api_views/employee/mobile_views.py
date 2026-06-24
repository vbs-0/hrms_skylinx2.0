from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from employee.models import Employee, EmployeeWorkInformation


class MobileEmployeeDirectoryAPIView(APIView):
    """Return a list of active employees for directory view."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            requesting_employee = request.user.employee_get
            company = requesting_employee.get_company()
        except Exception:
            company = None

        # Filter by company if resolvable
        if company:
            qs = Employee.objects.filter(
                employee_work_info__company_id=company,
                is_active=True
            ).select_related("employee_work_info", "employee_user_id").order_by(
                "employee_first_name"
            )
        else:
            qs = Employee.objects.filter(is_active=True).select_related(
                "employee_work_info", "employee_user_id"
            ).order_by("employee_first_name")

        directory = []
        for emp in qs:
            work_info = getattr(emp, "employee_work_info", None)
            dept = None
            designation = None
            manager_name = None
            try:
                if work_info:
                    if work_info.department_id:
                        dept = str(work_info.department_id.department)
                    if work_info.job_position_id:
                        designation = str(work_info.job_position_id.job_position)
                    if work_info.reporting_manager_id:
                        mgr = work_info.reporting_manager_id
                        manager_name = f"{mgr.employee_first_name} {mgr.employee_last_name}".strip()
            except Exception:
                pass

            profile_url = None
            try:
                if emp.employee_profile and emp.employee_profile.name:
                    profile_url = request.build_absolute_uri(emp.employee_profile.url)
            except Exception:
                pass

            directory.append({
                "id": str(emp.id),
                "employeeCode": emp.badge_id or f"EMP{emp.id}",
                "firstName": emp.employee_first_name or "",
                "lastName": emp.employee_last_name or "",
                "fullName": f"{emp.employee_first_name or ''} {emp.employee_last_name or ''}".strip(),
                "email": emp.email or "",
                "phone": emp.phone or "",
                "department": dept,
                "designation": designation,
                "reportingManager": manager_name,
                "gender": emp.gender or "",
                "profileUrl": profile_url,
            })

        return Response({"success": True, "message": "Directory loaded", "data": directory}, status=200)


class MobileOrgChartAPIView(APIView):
    """Return org chart as a tree starting from top-level employees (no manager)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            requesting_employee = request.user.employee_get
            company = requesting_employee.get_company()
        except Exception:
            company = None

        if company:
            all_employees = Employee.objects.filter(
                employee_work_info__company_id=company,
                is_active=True
            ).select_related("employee_work_info", "employee_work_info__reporting_manager_id",
                             "employee_work_info__job_position_id", "employee_work_info__department_id")
        else:
            all_employees = Employee.objects.filter(is_active=True).select_related(
                "employee_work_info"
            )

        # Build a flat list of nodes, each with parentId
        nodes = []
        for emp in all_employees:
            work_info = getattr(emp, "employee_work_info", None)
            manager_id = None
            designation = None
            dept = None
            try:
                if work_info:
                    if work_info.reporting_manager_id:
                        manager_id = str(work_info.reporting_manager_id.id)
                    if work_info.job_position_id:
                        designation = str(work_info.job_position_id.job_position)
                    if work_info.department_id:
                        dept = str(work_info.department_id.department)
            except Exception:
                pass

            profile_url = None
            try:
                if emp.employee_profile and emp.employee_profile.name:
                    profile_url = request.build_absolute_uri(emp.employee_profile.url)
            except Exception:
                pass

            nodes.append({
                "id": str(emp.id),
                "fullName": f"{emp.employee_first_name or ''} {emp.employee_last_name or ''}".strip(),
                "designation": designation,
                "department": dept,
                "profileUrl": profile_url,
                "parentId": manager_id,  # None means top-level
            })

        return Response({"success": True, "message": "Org chart loaded", "data": nodes}, status=200)
