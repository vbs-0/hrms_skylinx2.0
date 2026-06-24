from datetime import datetime
from django.db.models import Q
from django.urls import reverse
from django.conf import settings as pay_settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from payroll.models.models import Payslip, Reimbursement, Company
from payroll.models.tax_models import PayrollSettings
from employee.models import EmployeeWorkInformation
from payroll.views.views import generate_payslip_pdf, equalize_lists_length


class MobilePayslipListAPIView(APIView):
    """List payslips for the authenticated employee."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee", "data": []}, status=400)

        year_str = request.query_params.get("year")
        qs = Payslip.objects.filter(employee_id=employee).order_by("-start_date")

        if year_str:
            try:
                qs = qs.filter(start_date__year=int(year_str))
            except ValueError:
                pass

        payslips = []
        for p in qs:
            pay_head = p.pay_head_data or {}
            # Collect allowances and deductions from pay_head_data JSON
            allowances = []
            deductions = []
            # Extract allowances
            raw_allowances = pay_head.get("allowances", [])
            if isinstance(raw_allowances, list):
                for item in raw_allowances:
                    if isinstance(item, dict):
                        allowances.append({
                            "title": item.get("title") or item.get("name") or "—",
                            "amount": round(float(item.get("amount", 0) or 0), 2),
                        })

            # Extract all categories of deductions to match web layout zipping
            for d_cat in [
                "basic_pay_deductions",
                "gross_pay_deductions",
                "pretax_deductions",
                "post_tax_deductions",
                "tax_deductions",
                "net_deductions",
            ]:
                raw_deductions = pay_head.get(d_cat, [])
                if isinstance(raw_deductions, list):
                    for item in raw_deductions:
                        if isinstance(item, dict):
                            deductions.append({
                                "title": item.get("title") or item.get("name") or "—",
                                "amount": round(float(item.get("amount", 0) or 0), 2),
                            })

            pdf_url = request.build_absolute_uri(reverse("mobile-payslip-pdf", kwargs={"pk": p.id}))
            payslips.append({
                "id": str(p.id),
                "reference": p.reference or f"PS-{p.id}",
                "startDate": p.start_date.isoformat() if p.start_date else None,
                "endDate": p.end_date.isoformat() if p.end_date else None,
                "month": p.start_date.strftime("%B %Y") if p.start_date else None,
                "status": p.status or "draft",
                "basicPay": round(float(p.basic_pay or 0), 2),
                "grossPay": round(float(p.gross_pay or 0), 2),
                "totalDeductions": round(float(p.deduction or 0), 2),
                "netPay": round(float(p.net_pay or 0), 2),
                "contractWage": round(float(p.contract_wage or 0), 2),
                "paidDays": round(float(pay_head.get("paid_days", 0) or 0), 1),
                "lopDays": round(float(pay_head.get("unpaid_days", 0) or 0), 1),
                "taxableGrossPay": round(float(pay_head.get("taxable_gross_pay", 0) or 0), 2),
                "allowances": allowances,
                "deductions": deductions,
                "pdfUrl": pdf_url,
            })

        return Response({"success": True, "message": "Payslips loaded", "data": payslips}, status=200)


class MobileExpenseListAPIView(APIView):
    """List and create reimbursement/expense requests for the authenticated employee."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee", "data": []}, status=400)

        qs = Reimbursement.objects.filter(
            employee_id=employee,
            type="reimbursement"
        ).order_by("-allowance_on")

        expenses = []
        for r in qs:
            expenses.append({
                "id": str(r.id),
                "title": r.title,
                "amount": round(float(r.amount or 0), 2),
                "date": r.allowance_on.isoformat() if r.allowance_on else None,
                "status": r.status,
                "description": r.description or "",
            })

        return Response({"success": True, "message": "Expenses loaded", "data": expenses}, status=200)

    def post(self, request):
        try:
            employee = request.user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee"}, status=400)

        title = request.data.get("title", "").strip()
        amount = request.data.get("amount")
        date_str = request.data.get("date")
        description = request.data.get("description", "")

        if not title or not amount or not date_str:
            return Response({
                "success": False,
                "message": "title, amount, and date are required",
                "errorCode": "MISSING_FIELDS"
            }, status=400)

        try:
            expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            amount_val = float(amount)
        except (ValueError, TypeError):
            return Response({"success": False, "message": "Invalid amount or date format (YYYY-MM-DD)"}, status=400)

        reimbursement = Reimbursement.objects.create(
            title=title,
            type="reimbursement",
            employee_id=employee,
            allowance_on=expense_date,
            amount=amount_val,
            description=description,
            status="requested",
        )

        return Response({
            "success": True,
            "message": "Expense submitted successfully",
            "data": {
                "id": str(reimbursement.id),
                "title": reimbursement.title,
                "amount": reimbursement.amount,
                "status": reimbursement.status,
            }
        }, status=201)


class MobilePayslipPDFAPIView(APIView):
    """
    Generate and download the payslip PDF.
    Supports standard Bearer Token auth and query parameter auth (?token=<jwt>).
    """
    permission_classes = []

    def get(self, request, pk):
        user = None

        # 1. Try header auth
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                validated_token = JWTAuthentication().get_validated_token(auth_header.split(" ")[1])
                user = JWTAuthentication().get_user(validated_token)
            except Exception:
                pass

        # 2. Try query parameter auth (essential for webview/url_launcher redirection)
        if not user:
            token_param = request.query_params.get("token")
            if token_param:
                try:
                    validated_token = JWTAuthentication().get_validated_token(token_param)
                    user = JWTAuthentication().get_user(validated_token)
                except Exception:
                    pass

        if not user or not user.is_active:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)

        try:
            employee = user.employee_get
        except Exception:
            return Response({"success": False, "message": "Not an employee"}, status=400)

        try:
            payslip = Payslip.objects.get(id=pk)
        except Payslip.DoesNotExist:
            return Response({"success": False, "message": "Payslip not found"}, status=404)

        if payslip.employee_id != employee and not (user.is_superuser or user.has_perm("payroll.view_payslip")):
            return Response({"success": False, "message": "Permission denied"}, status=403)

        company = Company.objects.filter(hq=True).first()
        info = EmployeeWorkInformation.objects.filter(employee_id=employee)
        date_format = "MMM. D, YYYY"
        if info.exists():
            for data in info:
                employee_company = data.company_id
            company_name = Company.objects.filter(company=employee_company)
            emp_company = company_name.first()
            date_format = (
                emp_company.date_format
                if emp_company and emp_company.date_format
                else "MMM. D, YYYY"
            )

        data = payslip.pay_head_data or {}
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        if not start_date_str or not end_date_str:
            if payslip.start_date and payslip.end_date:
                start_date_str = payslip.start_date.strftime("%Y-%m-%d")
                end_date_str = payslip.end_date.strftime("%Y-%m-%d")
                data["start_date"] = start_date_str
                data["end_date"] = end_date_str
            else:
                return Response({"success": False, "message": "Date info missing in payslip"}, status=400)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        formatted_start_date = start_date_str
        formatted_end_date = end_date_str
        for format_name, format_string in pay_settings.SKYLINX_DATE_FORMATS.items():
            if format_name == date_format:
                formatted_start_date = start_date.strftime(format_string)
                formatted_end_date = end_date.strftime(format_string)

        if "allowances" not in data:
            data["allowances"] = []
        if "basic_pay_deductions" not in data:
            data["basic_pay_deductions"] = []
        if "gross_pay_deductions" not in data:
            data["gross_pay_deductions"] = []
        if "pretax_deductions" not in data:
            data["pretax_deductions"] = []
        if "post_tax_deductions" not in data:
            data["post_tax_deductions"] = []
        if "tax_deductions" not in data:
            data["tax_deductions"] = []
        if "net_deductions" not in data:
            data["net_deductions"] = []

        currency_symbol = "₹"
        settings_obj = PayrollSettings.objects.first()
        if settings_obj and settings_obj.currency_symbol:
            currency_symbol = settings_obj.currency_symbol

        data.update(
            {
                "month_start_name": start_date.strftime("%B %d, %Y"),
                "month_end_name": end_date.strftime("%B %d, %Y"),
                "formatted_start_date": formatted_start_date,
                "formatted_end_date": formatted_end_date,
                "employee": payslip.employee_id,
                "payslip": payslip,
                "json_data": data.copy(),
                "currency": currency_symbol,
                "all_deductions": [],
                "all_allowances": data["allowances"].copy(),
                "host": request.get_host(),
                "protocol": "https" if request.is_secure() else "http",
                "company": company,
            }
        )

        for deduction_list in [
            data["basic_pay_deductions"],
            data["gross_pay_deductions"],
            data["pretax_deductions"],
            data["post_tax_deductions"],
            data["tax_deductions"],
            data["net_deductions"],
        ]:
            data["all_deductions"].extend(deduction_list)

        equalize_lists_length(data["allowances"], data["all_deductions"])
        data["zipped_data"] = zip(data["allowances"], data["all_deductions"])
        data["request"] = request
        template_path = "payroll/payslip/payslip_pdf.html"

        html_flag = request.query_params.get("html", "false").lower() == "true"

        pdf_response = generate_payslip_pdf(template_path, context=data, html=html_flag)
        return pdf_response

