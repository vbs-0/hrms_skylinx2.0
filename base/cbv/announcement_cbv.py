"""
Announcement page
"""

import json
import os

from django.contrib import messages
from django.http import HttpResponse
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import AnnouncementForm
from base.methods import closest_numbers
from base.models import Announcement, AnnouncementView, Attachment, Company
from employee.models import Employee
from skylinx.http.response import SkylinxRedirect
from skylinx_auth.models import SkylinxUser
from skylinx_views.cbv_methods import hx_request_required, login_required, permission_required
from skylinx_views.generic.cbv.views import (
    SkylinxDetailedView,
    SkylinxFormView,
    SkylinxListView,
)
from notifications.signals import notify

BLOCKED_EXTENSIONS = {
    ".html",
    ".htm",
    ".js",
    ".svg",
    ".xml",
    ".php",
    ".py",
    ".sh",
    ".exe",
}


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
@method_decorator(permission_required(perm="base.add_announcement"), name="dispatch")
class AnnouncementFormView(SkylinxFormView):
    """
    form view for create button
    """

    form_class = AnnouncementForm
    model = Announcement
    new_display_title = _("Create Announcements.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Edit Announcement.")

        return context

    def form_valid(self, form: AnnouncementForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Announcement updated successfully.")
            else:
                message = _("Announcement created successfully.")

            anou, unused_attachment_ids = form.save(commit=False)

            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            # company_id may be present-but-empty in cleaned_data (.get default
            # won't kick in), so fall back to the creator's own company. Without
            # this the company-scoped manager hides the announcement from everyone.
            company = form.cleaned_data.get("company_id")
            if not company:
                emp = self.request.user.employee_get
                own = emp.get_company() if emp else None
                company = (
                    Company.objects.filter(id=own.id)
                    if own
                    else Company.objects.none()
                )

            if not (employees or departments or job_positions):
                employees = Employee.objects.filter(
                    employee_work_info__company_id__in=company, is_active=True
                )
                message = _(
                    f"Announcement created successfully to all employees in "
                    f"{', '.join(company.values_list('company', flat=True))}."
                )

            # Attachment validation
            files = self.request.FILES.getlist("attachments")
            safe_attachment_ids = []

            for file in files:
                ext = os.path.splitext(file.name)[1].lower()

                if ext in BLOCKED_EXTENSIONS:
                    messages.error(
                        self.request,
                        f"File type {ext} is not allowed for security reasons.",
                    )
                    continue

                attachment = Attachment.objects.create(file=file)
                safe_attachment_ids.append(attachment.id)

            anou.save()
            anou.attachments.set(safe_attachment_ids)  # IMPORTANT FIX
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            anou.company_id.set(company)  # scope to company or it stays hidden

            emp_dep = SkylinxUser.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = SkylinxUser.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )

            employees = employees | Employee.objects.filter(
                employee_work_info__department_id__in=departments
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__job_position_id__in=job_positions
            )

            anou.employees.add(*employees)

            # employees is Employee rows (not Users); notify.send needs Users.
            # This is the general "announce to all/selected employees" case —
            # emp_dep/emp_jobs below only cover department/job-position
            # targeting and miss it, so it silently created zero notifications
            # for a plain company-wide announcement.
            emp_users = SkylinxUser.objects.filter(employee_get__in=employees)
            notify.send(
                self.request.user.employee_get,
                recipient=emp_users,
                verb="A new announcement was posted.",
                verb_ar="تم نشر إعلان جديد.",
                verb_de="Eine neue Ankündigung wurde veröffentlicht.",
                verb_es="Se publicó un nuevo anuncio.",
                verb_fr="Une nouvelle annonce a été publiée.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                self.request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                self.request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            messages.success(self.request, message)
            return SkylinxRedirect(self.request)

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class AnnouncementDetailView(SkylinxDetailedView):

    model = Announcement
    template_name = "announcement/announcement_one.html"

    def get_context_data(self, **kwargs):
        import ast

        from skylinx.skylinx_middlewares import _thread_locals

        context = super().get_context_data(**kwargs)

        # Guard: if object was deleted or not found, close the modal gracefully
        if not self.instance:
            context["not_found"] = True
            context["extra_query"] = ""
            return context

        instance_ids = json.loads(self.request.GET.get("instance_ids", "[]"))
        url_info = resolve(self.request.path)
        url_name = url_info.url_name
        key = next(iter(url_info.kwargs), "pk")

        announcement_view_obj, _ = AnnouncementView.objects.get_or_create(
            user=self.request.user, announcement=self.instance
        )
        announcement_view_obj.viewed = True
        announcement_view_obj.save()

        if instance_ids:
            prev_id, next_id = closest_numbers(instance_ids, self.instance.pk)

            context.update(
                {
                    "instance_ids": str(instance_ids),
                    "ids_key": self.ids_key,
                    "next_url": reverse(url_name, kwargs={key: next_id}),
                    "previous_url": reverse(url_name, kwargs={key: prev_id}),
                }
            )

            get_params = self.request.GET.copy()
            get_params.pop(self.ids_key, None)
            context["extra_query"] = get_params.urlencode()
        else:
            context["extra_query"] = ""

        return context
