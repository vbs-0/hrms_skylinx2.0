"""
Forms for handling payroll-related operations.

This module provides Django ModelForms for creating and managing payroll-related data,
including filing status, tax brackets, and federal tax records.

The forms in this module inherit from the Django `forms.ModelForm` class and customize
the widget attributes to enhance the user interface and provide a better user experience.

"""

from django import forms
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from payroll.methods import federal_tax
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


class FilingStatusForm(ModelForm):
    """Form for creating and updating filing status."""

    cols = {
        "filing_status": 12,
        "based_on": 12,
        "description": 12,
    }

    class Meta:
        """Meta options for the form."""

        model = FilingStatus
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs: dict = self.fields["use_py"].widget.attrs
        self.fields["python_code"].required = False
        attrs[
            "onchange"
        ] = """
        if($(this).is(':checked')){
            $('#oc-editor').show();
            //$("#objectCreateModal #objectCreateModalTarget").css("max-width","90%")
        }else{
            //$("#objectCreateModal #objectCreateModalTarget").css("max-width","650px")
            $('#oc-editor').hide();
        }
        """

        if self.instance.pk is None:
            self.instance.python_code = federal_tax.CODE
        else:
            del self.fields["use_py"]
            del self.fields["python_code"]


class TaxBracketForm(ModelForm):
    """Form for creating and updating tax bracket."""

    cols = {"min_income": 12, "max_income": 12, "tax_rate": 12}

    class Meta:
        """Meta options for the form."""

        model = TaxBracket
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "filing_status_id": forms.HiddenInput(),
        }

from payroll.models.tax_models import Form16Document
from django.core.validators import FileExtensionValidator

class Form16DocumentForm(ModelForm):
    """Form for manually uploading a Form 16 document for an employee."""

    cols = {"employee": 12, "financial_year": 12, "document": 12}

    class Meta:
        model = Form16Document
        fields = ["employee", "financial_year", "document"]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control select2"}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].validators = [FileExtensionValidator(allowed_extensions=['pdf'])]

class Form16BulkUploadForm(forms.Form):
    """Form for bulk uploading Form 16 documents via a ZIP file."""
    
    financial_year = forms.CharField(
        max_length=9, 
        help_text="e.g., 2023-2024",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "2023-2024"})
    )
    zip_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['zip'])],
        help_text="Upload a ZIP file containing Form 16 PDFs. The PDFs must be named with the employee's Employee ID (e.g., EMP001.pdf).",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )

