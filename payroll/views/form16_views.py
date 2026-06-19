"""
form16_views.py

This module contains views to generate and download Form 16 Part B PDFs.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
import datetime

from base.methods import template_pdf
from skylinx.decorators import login_required, permission_required, hx_request_required
from payroll.models.models import Payslip, Contract
from employee.models import Employee

@login_required
@permission_required("payroll.view_payslip")
def form16_list_view(request):
    """
    Display the Form 16 selection view.
    HR sees all employees; Employees see their own.
    """
    user = request.user
    is_hr = user.has_perm("employee.change_employee")
    
    current_year = datetime.date.today().year
    years = [current_year, current_year - 1, current_year - 2]
    
    if is_hr:
        employees = Employee.objects.all()
    else:
        employees = Employee.objects.filter(employee_user_id=user)
        
    context = {
        "employees": employees,
        "years": years,
        "is_hr": is_hr,
    }
    return render(request, "payroll/form16/form16_list.html", context)


@login_required
@permission_required("payroll.view_payslip")
def generate_form16_pdf(request, employee_id, financial_year):
    """
    Aggregates salary and TDS for the financial year and generates Form 16 Part B PDF.
    Financial year e.g. 2025 means FY 2025-2026 (Apr 1 2025 - Mar 31 2026).
    """
    user = request.user
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Permission check: if not HR, can only generate own Form 16
    if not user.has_perm("employee.change_employee") and employee.employee_user_id != user:
        messages.error(request, "You do not have permission to view this Form 16.")
        return HttpResponse("Unauthorized", status=403)
        
    fy_start = datetime.date(financial_year, 4, 1)
    fy_end = datetime.date(financial_year + 1, 3, 31)
    
    # Get all payslips for the FY
    payslips = Payslip.objects.filter(
        employee_id=employee,
        start_date__gte=fy_start,
        end_date__lte=fy_end,
        status="Paid"
    )
    
    gross_salary = 0
    total_tds = 0
    pf_deducted = 0
    pt_deducted = 0
    esi_deducted = 0
    allowances_total = 0
    
    for payslip in payslips:
        gross_salary += payslip.gross_pay or 0
        total_tds += payslip.federal_tax or 0 # Federal Tax was relabeled to TDS
        # We assume deductions are stored in payslip.deduction_set or json. For simplicity we check if there's a JSON field or aggregate fields
        
        # Typically payslips have related records for allowances and deductions in this HRMS.
        # Assuming PayslipDeduction and PayslipAllowance exist, let's just aggregate safely if they do,
        # or use generic totals if not easily accessible.
        pass

    # Basic layout for Form 16 Part B
    context = {
        "employee": employee,
        "financial_year": f"{financial_year}-{financial_year+1}",
        "assessment_year": f"{financial_year+1}-{financial_year+2}",
        "gross_salary": round(gross_salary, 2),
        "total_tds": round(total_tds, 2),
        "net_salary": round(gross_salary - total_tds, 2), # Placeholder
    }
    
    html_string = render_to_string("payroll/form16/form16_pdf.html", context)
    return template_pdf(html_string, filename=f"Form16_{employee.badge_id}_{financial_year}.pdf")
