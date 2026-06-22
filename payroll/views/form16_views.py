"""
form16_views.py

This module contains views to list and upload Form 16 PDFs.
"""

import os
import zipfile
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, FileResponse
import datetime

from skylinx.decorators import login_required, permission_required
from employee.models import Employee
from payroll.models.tax_models import Form16Document
from payroll.forms.tax_forms import Form16DocumentForm, Form16BulkUploadForm
from django.core.files.base import ContentFile

@login_required
@permission_required("payroll.view_payslip")
def form16_list_view(request):
    """
    Display the Form 16 list view.
    HR sees all employees' uploaded Form 16s. Employees see their own.
    """
    user = request.user
    is_hr = user.has_perm("employee.change_employee")
    
    if is_hr:
        documents = Form16Document.objects.all().order_by("-financial_year", "employee__employee_first_name")
    else:
        documents = Form16Document.objects.filter(employee__employee_user_id=user).order_by("-financial_year")
        
    context = {
        "documents": documents,
        "is_hr": is_hr,
    }
    return render(request, "payroll/form16/form16_list.html", context)


@login_required
@permission_required("employee.change_employee")
def upload_form16(request):
    """
    Upload a single Form 16 document.
    """
    if request.method == "POST":
        form = Form16DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            # Check for existing document for this employee and year
            employee = form.cleaned_data["employee"]
            financial_year = form.cleaned_data["financial_year"]
            existing = Form16Document.objects.filter(employee=employee, financial_year=financial_year).first()
            if existing:
                existing.document = form.cleaned_data["document"]
                existing.save()
                messages.success(request, f"Form 16 updated for {employee} ({financial_year}).")
            else:
                form.save()
                messages.success(request, f"Form 16 uploaded successfully for {employee}.")
            return redirect("form16-list")
    else:
        form = Form16DocumentForm()
        
    context = {"form": form, "title": "Upload Form 16"}
    return render(request, "payroll/form16/form16_upload.html", context)


@login_required
@permission_required("employee.change_employee")
def bulk_upload_form16(request):
    """
    Bulk upload Form 16 PDFs via ZIP file.
    Matches filename (without .pdf) to Employee Badge ID.
    """
    if request.method == "POST":
        form = Form16BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            financial_year = form.cleaned_data["financial_year"]
            zip_file = form.cleaned_data["zip_file"]
            
            success_count = 0
            error_msgs = []
            
            try:
                with zipfile.ZipFile(zip_file, 'r') as archive:
                    for filename in archive.namelist():
                        if filename.endswith(".pdf"):
                            # Expecting "EMP001.pdf" -> badge_id "EMP001"
                            badge_id = os.path.splitext(os.path.basename(filename))[0]
                            employee = Employee.objects.filter(badge_id__iexact=badge_id).first()
                            
                            if employee:
                                pdf_data = archive.read(filename)
                                doc = Form16Document.objects.filter(employee=employee, financial_year=financial_year).first()
                                if not doc:
                                    doc = Form16Document(employee=employee, financial_year=financial_year)
                                
                                # Save the extracted file data to the document field
                                file_name_to_save = f"Form16_{badge_id}_{financial_year}.pdf"
                                doc.document.save(file_name_to_save, ContentFile(pdf_data), save=True)
                                success_count += 1
                            else:
                                error_msgs.append(f"No employee found with Badge ID: {badge_id}")
                                
                if success_count > 0:
                    messages.success(request, f"Successfully uploaded {success_count} Form 16 documents.")
                if error_msgs:
                    messages.warning(request, "Some files could not be matched: " + ", ".join(error_msgs[:5]) + ("..." if len(error_msgs)>5 else ""))
                    
                return redirect("form16-list")
            except zipfile.BadZipFile:
                messages.error(request, "Invalid ZIP file.")
    else:
        form = Form16BulkUploadForm()
        
    context = {"form": form, "title": "Bulk Upload Form 16"}
    return render(request, "payroll/form16/form16_bulk_upload.html", context)

@login_required
@permission_required("payroll.view_payslip")
def download_form16(request, pk):
    """
    Download a specific Form 16 document.
    """
    document = get_object_or_404(Form16Document, pk=pk)
    user = request.user
    
    # Permission check
    if not user.has_perm("employee.change_employee") and document.employee.employee_user_id != user:
        return HttpResponse("Unauthorized", status=403)
        
    if document.document:
        response = FileResponse(document.document.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Form16_{document.employee.badge_id}_{document.financial_year}.pdf"'
        return response
    return HttpResponse("File not found", status=404)

