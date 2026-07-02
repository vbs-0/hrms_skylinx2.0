"""
forms.py
"""

from typing import Any

from django import forms
from django.forms import widgets
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import Form, ModelForm
from base.rbac import current_company
from employee.forms import MultipleFileField
from employee.models import Employee
from payroll.context_processors import get_active_employees
from skylinx.skylinx_middlewares import _thread_locals
from payroll.models.models import (
    Contract,
    EncashmentGeneralSettings,
    PayrollGeneralSetting,
    ReimbursementFile,
    ReimbursementrequestComment,
)


class ContractForm(ModelForm):
    """
    ContactForm
    """

    verbose_name = _("Pay Register")
    contract_start_date = forms.DateField()
    contract_end_date = forms.DateField(required=False)
    ctc = forms.IntegerField(
        label=_("CTC"),
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "oh-input w-100",
                "placeholder": _("CTC"),
                "id": "id_ctc",
            }
        ),
    )
    basic_pct = forms.IntegerField(
        label=_("Basic (%)"),
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(
            attrs={
                "class": "oh-input w-100",
                "placeholder": _("Basic (%)"),
                "id": "id_basic_pct",
            }
        ),
    )

    class Meta:
        """
        Meta class for additional options
        """

        fields = "__all__"
        exclude = [
            "is_active",
            "contract_name",
        ]
        model = Contract

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].widget.attrs.update(
            {"onchange": "contractInitial(this)"}
        )
        self.fields["contract_start_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_end_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_status"].widget.attrs.update(
            {
                "class": "oh-select",
            }
        )
        if self.instance and self.instance.pk:
            dynamic_url = self.get_dynamic_hx_post_url(self.instance)
            self.fields["contract_status"].widget.attrs.update(
                {
                    "hx-target": "this",
                    "hx-post": dynamic_url,
                    "hx-swap": "beforebegin",
                }
            )
        if self.instance and self.instance.pk and self.instance.employee_id:
            from employee.models import EmployeeWorkInformation
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=self.instance.employee_id
            ).first()
            if work_info:
                self.fields["ctc"].initial = work_info.ctc
                self.fields["basic_pct"].initial = (
                    work_info.salary_components or {}
                ).get("basic", 50)
        field_order = [
            "employee_id",
            "contract_start_date",
            "contract_end_date",
            "wage_type",
            "ctc",
            "basic_pct",
            "wage",
            "filing_status",
            "contract_status",
            "department",
            "job_position",
            "job_role",
            "shift",
            "work_type",
            "pay_frequency",
            "notice_period_in_days",
            "contract_document",
            "deduct_leave_from_basic_pay",
            "calculate_daily_leave_amount",
            "deduction_for_one_leave_amount",
            "note",
        ]
        reordered_fields = {}
        for field_name in field_order:
            if field_name in self.fields:
                reordered_fields[field_name] = self.fields[field_name]
        for field_name, field in self.fields.items():
            if field_name not in reordered_fields:
                reordered_fields[field_name] = field
        self.fields = reordered_fields
        first = PayrollGeneralSetting.objects.first()
        if first and self.instance.pk is None:
            self.initial["notice_period_in_days"] = first.notice_period
        self.fields["contract_document"].widget.attrs[
            "accept"
        ] = ".jpg, .jpeg, .png, .pdf"

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("contract_form.html", context)
        return table_html

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.contract_name:
            instance.contract_name = f"{instance.employee_id}'s Pay Register"
        if instance.employee_id:
            from employee.models import EmployeeWorkInformation
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=instance.employee_id
            ).first()
            if work_info:
                ctc = self.cleaned_data.get("ctc")
                basic_pct = self.cleaned_data.get("basic_pct")
                if ctc is not None:
                    work_info.ctc = ctc
                if basic_pct is not None:
                    work_info.salary_components = {"basic": basic_pct}
                instance.wage = work_info.basic_salary
                if commit:
                    instance.save()
                    work_info.save()
            elif commit:
                instance.save()
        elif commit:
            instance.save()
        return instance

    def get_dynamic_hx_post_url(self, instance):
        """
        Render the url for contract status update through hx request
        """
        return f"/payroll/update-contract-status/{instance.pk}"


class ReimbursementRequestCommentForm(ModelForm):
    """
    ReimbursementRequestCommentForm form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ReimbursementrequestComment
        fields = ("comment",)


class reimbursementCommentForm(ModelForm):
    """
    Reimbursement request comment model form
    """

    verbose_name = "Add Comment"

    class Meta:
        """
        Meta class for additional options
        """

        model = ReimbursementrequestComment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["files"] = MultipleFileField(label="files")
        self.fields["files"].required = False
        self.fields["files"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        multiple_files_ids = []
        files = None
        if self.files.getlist("files"):
            files = self.files.getlist("files")
            self.instance.attachemnt = files[0]
            multiple_files_ids = []
            for attachemnt in files:
                file_instance = ReimbursementFile()
                file_instance.file = attachemnt
                file_instance.save()
                multiple_files_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.files.add(*multiple_files_ids)
        return instance, files


class EncashmentGeneralSettingsForm(ModelForm):
    class Meta:
        model = EncashmentGeneralSettings
        fields = "__all__"


class DashboardExport(Form):
    status_choices = [
        ("", ""),
        ("draft", "Draft"),
        ("review_ongoing", "Review Ongoing"),
        ("confirmed", "Confirmed"),
        ("paid", "Paid"),
    ]
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    employees = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.SelectMultiple,
    )
    status = forms.ChoiceField(required=False, choices=status_choices)
    contributions = forms.ChoiceField(
        required=False,
        choices=[
            (emp.id, emp.get_full_name())
            for emp in get_active_employees(None)["get_active_employees"]
        ],
        widget=forms.SelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        company = current_company(request) if request else None
        employees = Employee.objects.exclude(employee_user_id__is_superuser=True)
        if company:
            employees = employees.filter(employee_work_info__company_id=company)
        self.fields["employees"].choices = [
            (emp.id, emp.get_full_name()) for emp in employees
        ]
        self.fields["contributions"].choices = [
            (emp.id, emp.get_full_name())
            for emp in get_active_employees(None)["get_active_employees"]
            if not company
            or (
                getattr(emp, "employee_work_info", None)
                and emp.employee_work_info.company_id == company
            )
        ]
        self.fields["employees"].widget.attrs.update({"class": "oh-select oh-select-2"})
        self.fields["status"].widget.attrs.update({"class": "oh-select oh-select-2"})
        self.fields["contributions"].widget.attrs.update(
            {"class": "oh-select oh-select-2"}
        )
