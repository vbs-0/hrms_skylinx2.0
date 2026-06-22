import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS", "skylinx.settings.base")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from employee.models import Employee
from payroll.models.models import Contract, Payslip, Allowance, Deduction
from payroll.methods.methods import save_payslip, compute_salary_on_period
from base.models import Company

employee = Employee.objects.first()
if not employee:
    print("No employees found.")
    exit()

contract = Contract.objects.filter(employee_id=employee, contract_status="active").first()
if not contract:
    print("No active contract found, creating one...")
    company = Company.objects.first()
    contract = Contract.objects.create(
        employee_id=employee,
        contract_name="Test Contract",
        wage_type="monthly",
        wage=5000,
        contract_status="active",
        contract_start_date=date(2023, 1, 1),
    )

start_date = date.today().replace(day=1)
end_date = date.today()

salary_data = compute_salary_on_period(employee, start_date, end_date)
if salary_data is None:
    print("Could not compute salary. Contract exists but calculation failed.")
    exit()

basic_pay = salary_data.get('basic_pay', 0)
gross_pay = basic_pay
deduction = salary_data.get('loss_of_pay', 0)
net_pay = gross_pay - deduction

payslip_data = {
    "employee": employee,
    "start_date": start_date,
    "end_date": end_date,
    "status": "draft",
    "basic_pay": basic_pay,
    "contract_wage": salary_data.get('contract_wage', 0),
    "gross_pay": gross_pay,
    "deduction": deduction,
    "net_pay": net_pay,
    "pay_data": {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "basic_pay": float(basic_pay),
        "gross_pay": float(gross_pay),
        "net_pay": float(net_pay),
        "pretax_deductions": [],
        "post_tax_deductions": [],
        "tax_deductions": [],
        "net_deductions": [],
        "allowances": [],
        "basic_pay_deductions": [],
        "gross_pay_deductions": []
    },
    "installments": []
}

payslip = save_payslip(**payslip_data)
print(f"Payslip generated successfully for {employee}! Payslip ID: {payslip.id}")
