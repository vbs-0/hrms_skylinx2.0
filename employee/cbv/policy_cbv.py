"""
Policy  forms
"""

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.filters import PolicyFilter
from employee.forms import PolicyForm
from employee.models import Policy
from skylinx_views.cbv_methods import login_required, permission_required
from skylinx_views.generic.cbv.views import SkylinxFormView, SkylinxNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="employee.add_policy"), name="dispatch")
class PolicyFormView(SkylinxFormView):
    """
    form view for create policy
    """

    form_class = PolicyForm
    model = Policy
    new_display_title = _("Policy Creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Policy Update")
        return context

    def form_valid(self, form: PolicyForm) -> HttpResponse:
        if form.is_valid():
            is_new = form.instance.pk is None
            if form.instance.pk:
                message = _("Policy saved")
            else:
                message = _("Policy updated")
            policy, _attachments = form.save()
            if is_new:
                from base.models import Company
                selected_company = self.request.session.get("selected_company")
                company = None
                if selected_company and selected_company != "all":
                    company = Company.objects.filter(id=selected_company).first()
                if not company and hasattr(self.request.user, "employee_get") and self.request.user.employee_get:
                    work_info = getattr(self.request.user.employee_get, "employee_work_info", None)
                    if work_info:
                        company = work_info.company_id
                if not company:
                    company = Company.objects.first()
                if company:
                    policy.company_id.add(company)
            messages.success(self.request, _(message))
            return self.HttpResponse(targets_to_reload=["#policyContainerReload"])

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class PoliciesNav(SkylinxNavView):
    """
    Policies Nav
    """

    nav_title = _("Policies")
    search_url = reverse_lazy("search-policies")
    search_swap_target = "#policyContainer"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("employee.add_policy"):
            self.create_attrs = ""
        else:
            self.create_attrs = f"""
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{reverse_lazy('create-policy')}"
                hx-target="#genericModalBody"
            """
        return super().dispatch(request, *args, **kwargs)
