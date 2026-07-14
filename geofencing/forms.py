from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm

from .models import GeoFencing


class GeoFencingSetupForm(ModelForm):
    verbose_name = _("Geofence Configuration")

    class Meta:
        model = GeoFencing
        exclude = ["company_id"]
        widgets = {
            "exempted_employees": forms.SelectMultiple(
                attrs={"class": "oh-select oh-select-2", "id": "id_exempted_employees"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from skylinx.skylinx_middlewares import _thread_locals
        from base.rbac import current_company
        from employee.models import Employee

        request = getattr(_thread_locals, "request", None)
        company = current_company(request) if request else None
        qs = Employee.objects.all()
        if company:
            qs = qs.filter(employee_work_info__company_id=company)
        self.fields["exempted_employees"].queryset = qs

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
