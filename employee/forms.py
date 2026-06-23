"""
forms.py

This module contains the form classes used in the application.

Each form represents a specific functionality or data input in the
application. They are responsible for validating
and processing user input data.

Classes:
- YourForm: Represents a form for handling specific data input.

Usage:
from django import forms

class YourForm(forms.Form):
    field_name = forms.CharField()

    def clean_field_name(self):
        # Custom validation logic goes here
        pass
"""

import logging
import re
from datetime import date, datetime
from typing import Any

from django import forms
from django.db.models import Q
from django.forms import DateInput, TextInput
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.methods import eval_validate, reload_queryset
from employee.models import (
    Actiontype,
    BonusPoint,
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeGeneralSetting,
    EmployeeNote,
    EmployeeTag,
    EmployeeWorkInformation,
    NoteFiles,
    Policy,
    PolicyMultipleFile,
)
from skylinx import skylinx_middlewares
from skylinx_audit.models import AccountBlockUnblock
from skylinx_auth.models import SkylinxUser

logger = logging.getLogger(__name__)


class ModelForm(forms.ModelForm):
    """
    Override of Django ModelForm to add initial styling and defaults.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        reload_queryset(self.fields)

        request = getattr(skylinx_middlewares._thread_locals, "request", None)

        today = date.today()
        now = datetime.now()

        default_input_class = "oh-input w-100"
        select_class = "oh-select"
        checkbox_class = "oh-switch__checkbox"

        for field_name, field in self.fields.items():
            widget = field.widget
            label = _(field.label) if field.label else ""

            # Date field
            if isinstance(widget, forms.DateInput):
                field.initial = today
                widget.input_type = "date"
                widget.format = "%Y-%m-%d"
                field.input_formats = ["%Y-%m-%d"]

                existing_class = widget.attrs.get("class", default_input_class)
                widget.attrs.update(
                    {
                        "class": f"{existing_class} form-control",
                        "placeholder": label,
                    }
                )

            # Time field
            elif isinstance(widget, forms.TimeInput):
                field.initial = now.strftime("%H:%M")
                widget.input_type = "time"
                widget.format = "%H:%M"
                field.input_formats = ["%H:%M"]

                existing_class = widget.attrs.get("class", default_input_class)
                widget.attrs.update(
                    {
                        "class": f"{existing_class} form-control",
                        "placeholder": label,
                    }
                )

            # Number, Email, Text, File, URL fields
            elif isinstance(
                widget,
                (
                    forms.NumberInput,
                    forms.EmailInput,
                    forms.TextInput,
                    forms.FileInput,
                    forms.URLInput,
                ),
            ):
                existing_class = widget.attrs.get("class", default_input_class)
                widget.attrs.update(
                    {
                        "class": f"{existing_class} form-control",
                        "placeholder": _(field.label.title()) if field.label else "",
                    }
                )

            # Select fields
            elif isinstance(widget, forms.Select):
                if not isinstance(field, forms.ModelMultipleChoiceField):
                    field.empty_label = _("---Choose {label}---").format(label=label)
                existing_class = widget.attrs.get("class", select_class)
                widget.attrs.update({"class": existing_class})

            # Textarea
            elif isinstance(widget, forms.Textarea):
                existing_class = widget.attrs.get("class", default_input_class)
                widget.attrs.update(
                    {
                        "class": f"{existing_class} form-control",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )

            # Checkbox types
            elif isinstance(
                widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)
            ):
                existing_class = widget.attrs.get("class", checkbox_class)
                widget.attrs.update({"class": existing_class})

        # Set employee_id and company_id once
        if request:
            employee = getattr(request.user, "employee_get", None)
            if employee:
                if "employee_id" in self.fields and self._meta.model.__name__ not in [
                    "DisciplinaryAction"
                ]:
                    self.fields["employee_id"].initial = employee

                if "company_id" in self.fields:
                    company_field = self.fields["company_id"]
                    company = getattr(employee, "get_company", None)
                    if company:
                        queryset = company_field.queryset
                        company_field.initial = (
                            company if company in queryset else queryset.first()
                        )


class UserForm(ModelForm):
    """
    Form for SkylinxUser model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups",)
        model = SkylinxUser


class UserPermissionForm(ModelForm):
    """
    Form for SkylinxUser model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups", "user_permissions")
        model = SkylinxUser


class EmployeeForm(ModelForm):
    """
    Form for Employee model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Employee
        fields = "__all__"
        exclude = (
            "employee_user_id",
            "additional_info",
            "is_from_onboarding",
            "is_directly_converted",
            "is_active",
            "account_type",
        )
        widgets = {
            "dob": TextInput(attrs={"type": "date", "id": "dob"}),
        }
        labels = {
            "email": _("Official Email ID"),
            "phone": _("Phone Number"),
            "employee_first_name": _("First Name"),
            "employee_last_name": _("Last Name"),
            "dob": _("Date of Birth"),
            "badge_id": _("Employee ID"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["phone"].widget.attrs["autocomplete"] = "phone"
        self.fields["address"].widget.attrs["autocomplete"] = "address"
        if instance := kwargs.get("instance"):
            # ----
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # ----
            initial = {}
            if instance.dob is not None:
                initial["dob"] = instance.dob.strftime("%H:%M")
            kwargs["initial"] = initial
        else:
            self.initial = {"badge_id": self.get_next_badge_id()}
        if not self.instance or not self.instance.pk:
            self.initial["country"] = "India"


        # ── India Localization: PAN / Aadhaar / Account Type ────────────────
        if "pan_number" in self.fields:
            self.fields["pan_number"].required = True
            self.fields["pan_number"].widget.attrs.update({
                "placeholder": "ABCDE1234F",
                "style": "text-transform:uppercase",
                "maxlength": "10",
            })
        if "aadhaar_number" in self.fields:
            self.fields["aadhaar_number"].required = True
            self.fields["aadhaar_number"].widget.attrs.update({
                "placeholder": "xxxx xxxx xxxx",
                "maxlength": "12",
                "inputmode": "numeric",
            })

        if "account_type" in self.fields:
            self.fields["account_type"].required = False

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)

    def clean_pan_number(self):
        """Validate PAN format: 5 letters, 4 digits, 1 letter (ABCDE1234F)."""
        import re as _re
        pan = self.cleaned_data.get("pan_number")
        if pan:
            pan = pan.upper().strip()
            if not _re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
                raise forms.ValidationError(
                    _("Invalid PAN format. Must be like ABCDE1234F.")
                )
        return pan or None

    def clean_aadhaar_number(self):
        """Validate Aadhaar: exactly 12 digits."""
        import re as _re
        aadhaar = self.cleaned_data.get("aadhaar_number")
        if aadhaar:
            aadhaar = aadhaar.replace(" ", "").strip()
            if not _re.match(r"^\d{12}$", aadhaar):
                raise forms.ValidationError(
                    _("Aadhaar number must be exactly 12 digits.")
                )
        return aadhaar or None

    def clean(self):

        super().clean()
        # License cap: block creating a NEW active employee past the plan limit,
        # surfaced as a normal form error (popup) instead of the cap signal's
        # hard 403/timeout. Only on create — editing an existing one is fine.
        if not (self.instance and self.instance.id):
            from licensing import service

            if service.employee_cap_reached():
                raise forms.ValidationError(
                    _(
                        "License limit reached: your plan allows %s active "
                        "employees. Upgrade your subscription to add more."
                    )
                    % service.employee_limit()
                )
        email = self.cleaned_data["email"]
        query = Employee.objects.entire().filter(email=email)
        if self.instance and self.instance.id:
            query = query.exclude(id=self.instance.id)

        existing_employee = query.first()

        if existing_employee:
            company_id = None
            if (
                hasattr(existing_employee, "employee_work_info")
                and existing_employee.employee_work_info
            ):
                company_id = existing_employee.employee_work_info.company_id

            if company_id:
                error_message = _(
                    "An Employee with this Email already exists in company {}".format(
                        company_id
                    )
                )
            else:
                error_message = _("An Employee with this Email already exists")

            raise forms.ValidationError({"email": error_message})

    def get_next_badge_id(self):
        """
        This method is used to generate badge id
        """
        from django.db.models import Max
        max_id = Employee.objects.entire().aggregate(max_id=Max('id'))['max_id']
        return str((max_id or 0) + 1)

    def clean_badge_id(self):
        """
        This method is used to clean the badge id
        """
        badge_id = self.cleaned_data["badge_id"]
        if badge_id:
            all_employees = Employee.objects.entire()
            queryset = all_employees.filter(badge_id=badge_id).exclude(
                pk=self.instance.pk if self.instance else None
            )
            if queryset.exists():
                raise forms.ValidationError(_("Employee ID must be unique."))
            if not re.search(r"\d", badge_id):
                raise forms.ValidationError(
                    _("Employee ID must contain at least one digit.")
                )
        return badge_id


class EmployeeWorkInformationForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeWorkInformation
        fields = "__all__"
        exclude = ("employee_id", "additional_info", "experience", "tags", "salary_hour")

        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "job_position_id": _("Designation"),
            "job_role_id": _("Job Title"),
            "location": _("Work Location"),
            "date_joining": _("Date of Joining"),
            "employee_type_id": _("Employee Type"),
            "reporting_manager_id": _("Reporting Manager"),
            "department_id": _("Department"),
            "company_id": _("Company"),
            "ctc": _("CTC"),
            "probation_days": _("Probation Period (Days)"),
            "salary_components": _("Salary Components (%)"),
        }

    def __init__(self, *args, disable=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"

        self.fields["job_position_id"].widget.attrs.update(
            {
                "onchange": "jobChange($(this))",
            }
        )

        for field in self.fields:
            self.fields[field].widget.attrs["placeholder"] = self.fields[field].label
            if disable:
                self.fields[field].disabled = True
        field_names = {
            "Department": "department",
            "Designation": "job_position",   # was "Job Position"
            "Job Title": "job_role",           # was "Job Role"
            "Work Type": "work_type",
            "Employee Type": "employee_type",
            "Shift": "employee_shift",
        }
        urls = {
            "Department": "#dynamicDept",
            "Designation": "#dynamicJobPosition",   # was "Job Position"
            "Job Title": "#dynamicJobRole",          # was "Job Role"
            "Work Type": "#dynamicWorkType",
            "Employee Type": "#dynamicEmployeeType",
            "Shift": "#dynamicShift",
        }

        for label, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField) and field.label in field_names:
                if field.label is not None:
                    field_name = field_names.get(field.label)
                    if field.queryset.model != Employee and field_name:
                        translated_label = _(field.label)
                        empty_label = _("---Choose {label}---").format(
                            label=translated_label
                        )
                        self.fields[label] = forms.ChoiceField(
                            choices=[("", empty_label)]
                            + list(field.queryset.values_list("id", f"{field_name}")),
                            required=field.required,
                            label=translated_label,
                            initial=field.initial,
                            widget=forms.Select(
                                attrs={
                                    "class": "oh-select",
                                    "onchange": f'onDynamicCreate(this.value,"{urls.get(field.label)}");',
                                }
                            ),
                        )
                        self.fields[label].choices += [
                            ("create", _("Create New {} ").format(translated_label))
                        ]

    def clean(self):
        cleaned_data = super().clean()
        if "employee_id" in self.errors:
            del self.errors["employee_id"]
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Multi-tenant safety: never leave company blank. A company-less work
        # info row leaks the employee into EVERY tenant's list (manager's
        # __isnull clause), so default to the acting user's company.
        if instance.company_id is None:
            instance.company_id = _default_company_id()
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)


def _default_company_id():
    """The Company the acting user is in, used to stamp company-less records."""
    from base.models import Company

    cid = skylinx_middlewares.get_selected_company()
    if cid and cid != "all":
        return Company.objects.filter(id=cid).first()
    request = getattr(skylinx_middlewares._thread_locals, "request", None)
    if request and getattr(request, "user", None) and request.user.is_authenticated:
        try:
            return request.user.employee_get.employee_work_info.company_id
        except Exception:
            return None
    return None


class EmployeeWorkInformationUpdateForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeWorkInformation
        fields = "__all__"
        # fields = [
        #     "department_id",
        #     "job_position_id",
        #     "job_role_id",
        #     "work_type_id",
        #     "employee_type_id",
        #     "reporting_manager_id",
        #     "company_id",
        #     "tags",
        #     "location",
        #     "email",
        #     "mobile",
        #     "shift_id",
        #     "date_joining",
        #     "contract_end_date",
        #     "basic_salary",
        #     "salary_hour",
        # ]
        exclude = ("employee_id", "experience", "additional_info", "tags")

        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
            "probation_end": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "job_position_id": _("Designation"),
            "job_role_id": _("Job Title"),
            "location": _("Work Location"),
            "date_joining": _("Date of Joining"),
            "employee_type_id": _("Employee Type"),
            "reporting_manager_id": _("Reporting Manager"),
            "department_id": _("Department"),
            "company_id": _("Company"),
            "basic_salary": _("CTC"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department_id"].widget.attrs.update(
            {
                "hx-target": "#id_job_position_id_parent_div",
                "hx-include": "#id_job_position_id",
                "hx-trigger": "change,load",
                "hx-swap": "innerHTML",
                "hx-get": "/employee/get-job-positions-hx",
            }
        )
        self.fields["job_position_id"].widget.attrs.update(
            {
                "hx-target": "#id_job_role_id_parent_div",
                "hx-include": "#id_job_role_id",
                "hx-trigger": "change,load",
                "hx-swap": "innerHTML",
                "hx-get": "/employee/get-job-roles-hx",
            }
        )

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)


class EmployeeBankDetailsForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    account_type = forms.ChoiceField(
        choices=[("", _("---Choose Account Type---"))] + Employee.ACCOUNT_TYPE_CHOICES,
        required=False,
        label=_("Bank Account Type"),
        initial="savings",
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = (
            "any_other_code1",
            "bank_name",
            "branch",
            "account_type",
            "account_number",
            "city",
            "state",
            "country",
        )
        labels = {
            "any_other_code1": _("IFSC Code"),
            "bank_name": _("Account Name"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["account_type"] = "savings"
        self.initial["country"] = "India"
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "oh-input w-100"
        if self.instance and hasattr(self.instance, "employee_id") and self.instance.employee_id:
            self.initial["account_type"] = self.instance.employee_id.account_type or "savings"
        if self.instance and self.instance.country:
            self.initial["country"] = self.instance.country



    def clean_any_other_code1(self):
        ifsc = self.cleaned_data.get("any_other_code1")
        if ifsc and not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc):
            raise forms.ValidationError(_("Invalid IFSC Code. Format should be 4 letters, '0', then 6 alphanumeric characters."))
        return ifsc

    def save(self, commit=True):
        bank_details = super().save(commit=False)
        account_type = self.cleaned_data.get("account_type")
        
        orig_save = bank_details.save
        def custom_save(*args, **kwargs):
            orig_save(*args, **kwargs)
            if bank_details.employee_id:
                employee = bank_details.employee_id
                if employee.account_type != account_type:
                    employee.account_type = account_type
                    employee.save(update_fields=["account_type"])
        bank_details.save = custom_save
        
        if commit:
            bank_details.save()
        return bank_details


class EmployeeBankDetailsUpdateForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    account_type = forms.ChoiceField(
        choices=[("", _("---Choose Account Type---"))] + Employee.ACCOUNT_TYPE_CHOICES,
        required=False,
        label=_("Bank Account Type"),
        initial="savings",
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = (
            "any_other_code1",
            "bank_name",
            "branch",
            "account_type",
            "account_number",
            "city",
            "state",
            "country",
        )
        labels = {
            "any_other_code1": _("IFSC Code"),
            "bank_name": _("Account Name"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["account_type"] = "savings"
        self.initial["country"] = "India"
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "oh-input w-100"
        for field in self.fields:
            self.fields[field].widget.attrs["placeholder"] = self.fields[field].label
        if self.instance and hasattr(self.instance, "employee_id") and self.instance.employee_id:
            self.initial["account_type"] = self.instance.employee_id.account_type or "savings"
        if self.instance and self.instance.country:
            self.initial["country"] = self.instance.country

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/update_form/bank_info_as_p.html", context)

    def clean_any_other_code1(self):
        ifsc = self.cleaned_data.get("any_other_code1")
        if ifsc and not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc):
            raise forms.ValidationError(_("Invalid IFSC Code. Format should be 4 letters, '0', then 6 alphanumeric characters."))
        return ifsc

    def save(self, commit=True):
        bank_details = super().save(commit=False)
        account_type = self.cleaned_data.get("account_type")
        
        orig_save = bank_details.save
        def custom_save(*args, **kwargs):
            orig_save(*args, **kwargs)
            if bank_details.employee_id:
                employee = bank_details.employee_id
                if employee.account_type != account_type:
                    employee.account_type = account_type
                    employee.save(update_fields=["account_type"])
        bank_details.save = custom_save
        
        if commit:
            bank_details.save()
        return bank_details


excel_columns = [
    ("badge_id", _("Employee ID")),
    ("employee_first_name", _("First Name")),
    ("employee_last_name", _("Last Name")),
    ("email", _("Email")),
    ("phone", _("Phone")),
    ("experience", _("Experience")),
    ("gender", _("Gender")),
    ("dob", _("Date of Birth")),
    ("country", _("Country")),
    ("state", _("State")),
    ("city", _("City")),
    ("address", _("Address")),
    ("zip", _("PIN Code")),
    ("marital_status", _("Marital Status")),
    ("children", _("Children")),
    ("is_active", _("Is active")),
    ("emergency_contact", _("Emergency Contact")),
    ("emergency_contact_name", _("Emergency Contact Name")),
    ("emergency_contact_relation", _("Emergency Contact Relation")),
    ("employee_work_info__email", _("Work Email")),
    ("employee_work_info__mobile", _("Work Phone")),
    ("employee_work_info__department_id", _("Department")),
    ("employee_work_info__job_position_id", _("Designation")),
    ("employee_work_info__job_role_id", _("Job Role")),
    ("employee_work_info__shift_id", _("Shift")),
    ("employee_work_info__work_type_id", _("Work Mode")),
    ("employee_work_info__reporting_manager_id", _("Reporting Manager")),
    ("employee_work_info__employee_type_id", _("Employment Type")),
    ("employee_work_info__location", _("Location")),
    ("employee_work_info__date_joining", _("Date Joining")),
    ("employee_work_info__basic_salary", _("Basic Salary")),
    ("employee_work_info__salary_hour", _("Salary Hour")),
    ("employee_work_info__contract_end_date", _("Contract End Date")),
    ("employee_work_info__company_id", _("Company")),
    ("employee_bank_details__bank_name", _("Bank Name")),
    ("employee_bank_details__branch", _("Branch")),
    ("employee_bank_details__account_number", _("Account Number")),
    ("employee_bank_details__any_other_code1", _("IFSC Code")),
    ("employee_bank_details__any_other_code2", _("Bank Code #2")),
    ("employee_bank_details__country", _("Bank Country")),
    ("employee_bank_details__state", _("Bank State")),
    ("employee_bank_details__city", _("Bank City")),
    # ── India Localization fields ──────────────────────────────────────────
    ("pan_number", _("PAN Number")),
    ("aadhaar_number", _("Aadhaar Number")),
    ("account_type", _("Bank Account Type")),
]
fields_to_remove = [
    "badge_id",
    "employee_first_name",
    "employee_last_name",
    "is_active",
    "email",
    "phone",
    "employee_bank_details__account_number",
]


class EmployeeExportExcelForm(forms.Form):
    selected_fields = forms.MultipleChoiceField(
        choices=excel_columns,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "badge_id",
            "employee_first_name",
            "employee_last_name",
            "email",
            "phone",
            "gender",
            "employee_work_info__department_id",
            "employee_work_info__job_position_id",
            "employee_work_info__job_role_id",
            "employee_work_info__shift_id",
            "employee_work_info__work_type_id",
            "employee_work_info__reporting_manager_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__location",
            "employee_work_info__date_joining",
            "employee_work_info__basic_salary",
            "employee_work_info__salary_hour",
            "employee_work_info__contract_end_date",
            "employee_work_info__company_id",
        ],
    )


class BulkUpdateFieldForm(forms.Form):
    update_fields = forms.MultipleChoiceField(
        choices=excel_columns, label=_("Select Fields to Update")
    )
    bulk_employee_ids = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        updated_choices = [
            (value, label)
            for value, label in self.fields["update_fields"].choices
            if value not in fields_to_remove
        ]
        self.fields["update_fields"].choices = updated_choices
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "oh-select oh-input w-100"


class EmployeeNoteForm(ModelForm):
    """
    Form for EmployeeNote model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeNote
        fields = ("description",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note_files"] = MultipleFileField(label="files")
        self.fields["note_files"].required = False

    def save(self, commit: bool = ...) -> Any:
        attachement = []
        multiple_attachment_ids = []
        attachements = None
        if self.files.getlist("note_files"):
            attachements = self.files.getlist("note_files")
            self.instance.attachement = attachements[0]
            multiple_attachment_ids = []

            for attachement in attachements:
                file_instance = NoteFiles()
                file_instance.files = attachement
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.note_files.add(*multiple_attachment_ids)
        return instance, multiple_attachment_ids


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        if len(result) == 0:
            result = [[]]
        return result[0]


class PolicyForm(ModelForm):
    """
    PolicyForm
    """

    cols = {"title": 12, "body": 12, "is_visible_to_all": 12, "company_id": 12}

    class Meta:
        model = Policy
        fields = "__all__"
        exclude = ["attachments", "is_active", "company_id"]
        widgets = {
            "body": forms.Textarea(
                attrs={"data-summernote": "", "style": "display:none;"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachment"] = MultipleFileField(
            label="Attachements", required=False
        )

    def save(self, *args, commit=True, **kwargs):
        attachemnt = []
        multiple_attachment_ids = []
        attachemnts = None
        if self.files.getlist("attachment"):
            attachemnts = self.files.getlist("attachment")
            multiple_attachment_ids = []
            for attachemnt in attachemnts:
                file_instance = PolicyMultipleFile()
                file_instance.attachment = attachemnt
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.attachments.add(*multiple_attachment_ids)
        return instance, attachemnts


class BonusPointAddForm(ModelForm):
    class Meta:
        model = BonusPoint
        fields = ["points", "reason"]
        widgets = {
            "reason": forms.TextInput(attrs={"required": "required"}),
        }


class BonusPointRedeemForm(ModelForm):
    class Meta:
        model = BonusPoint
        fields = ["points"]

    def clean(self):
        cleaned_data = super().clean()
        available_points = BonusPoint.objects.filter(
            employee_id=self.instance.employee_id
        ).first()
        if not available_points or available_points.points < cleaned_data["points"]:
            raise forms.ValidationError({"points": "Not enough bonus points to redeem"})
        if cleaned_data["points"] <= 0:
            raise forms.ValidationError(
                {"points": "Points must be greater than zero to redeem."}
            )


class DisciplinaryActionForm(ModelForm):
    class Meta:
        model = DisciplinaryAction
        fields = "__all__"
        exclude = ["objects", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
        }

    action = forms.ModelChoiceField(
        queryset=Actiontype.objects.all(),
        label=_("Action"),
        widget=forms.Select(
            attrs={
                "class": "oh-select",
                "onchange": "actionTypeChange($(this))",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        action_choices = [("", _("---Choose Action---"))] + list(
            self.fields["action"].queryset.values_list("id", "title")
        )
        self.fields["action"].choices = action_choices
        if self.instance.pk is None:
            self.fields["action"].choices += [("create", _("Create new action type "))]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class ActiontypeForm(ModelForm):

    cols = {"title": 12, "action_type": 12}

    class Meta:
        model = Actiontype
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["action_type"].widget.attrs.update(
            {
                "onchange": "actionChange($(this))",
            }
        )


class EmployeeTagForm(ModelForm):
    """
    Employee Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeTag
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {"color": TextInput(attrs={"type": "color", "style": "height:50px"})}


class EmployeeGeneralSettingPrefixForm(forms.ModelForm):

    class Meta:

        model = EmployeeGeneralSetting
        exclude = ["objects"]
        widgets = {
            "badge_id_prefix": forms.TextInput(attrs={"class": "oh-input w-100"}),
            "company_id": forms.Select(attrs={"class": "oh-select oh-select-2 w-100"}),
        }
