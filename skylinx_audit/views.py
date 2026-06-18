"""
views.py
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from skylinx.http.response import SkylinxRedirect
from skylinx_audit.forms import (
    AuditModelConfigForm,
    AuditModelFieldsForm,
    field_choices_for,
)
from skylinx_audit.models import AuditModelConfig
from skylinx_audit.registry import DEFAULT_TRACKED_MODELS


@login_required
@permission_required("skylinx_audit.view_auditmodelconfig")
def audit_model_settings(request):
    """Render the audit-tracking configuration card."""

    form = AuditModelConfigForm()
    configs = AuditModelConfig.objects.all().order_by("app_label", "model_name")
    context = {
        "audit_model_form": form,
        "audit_model_configs": configs,
    }
    return render(
        request,
        "skylinx_audit/audit_model_settings.html",
        context,
    )


@login_required
@permission_required("skylinx_audit.change_auditmodelconfig")
@require_http_methods(["POST"])
def save_audit_models(request):
    """Persist the list of audit-tracked models."""

    selected = request.POST.getlist("model_paths")
    selected_pairs = []
    for path in selected:
        if "." not in path:
            continue
        app_label, model_name = path.split(".", 1)
        selected_pairs.append((app_label, model_name))

    # Built-in defaults are always tracked — they cannot be turned off here
    # so audit history never silently disappears for the core Employee models.
    default_set = set(DEFAULT_TRACKED_MODELS)
    selected_set = set(selected_pairs) | default_set
    existing = {(c.app_label, c.model_name): c for c in AuditModelConfig.objects.all()}

    # Remove configs that were unchecked, but never delete defaults.
    for key, cfg in existing.items():
        if key in selected_set or key in default_set:
            continue
        cfg.delete()

    # Create new configs for newly checked entries (and ensure defaults exist).
    for app_label, model_name in selected_set:
        if (app_label, model_name) not in existing:
            AuditModelConfig.objects.create(
                app_label=app_label,
                model_name=model_name,
                is_enabled=True,
                tracked_fields=[],
            )

    messages.success(request, _("Audit tracking configuration updated."))

    if request.headers.get("HX-Request"):
        return HttpResponse(
            status=200,
            headers={"HX-Redirect": reverse("audit-model-settings")},
        )
    return SkylinxRedirect(request)


@login_required
@permission_required("skylinx_audit.change_auditmodelconfig")
def edit_audit_model_fields(request, pk):
    """Edit which fields of a single model are tracked."""

    try:
        config = AuditModelConfig.objects.get(pk=pk)
    except AuditModelConfig.DoesNotExist:
        return HttpResponseBadRequest("Audit configuration not found.")

    if request.method == "POST":
        form = AuditModelFieldsForm(
            request.POST,
            app_label=config.app_label,
            model_name=config.model_name,
        )
        if form.is_valid():
            config.tracked_fields = form.cleaned_data["fields_to_track"]
            config.save()
            messages.success(
                request,
                _("Tracked fields updated for %(model)s.")
                % {"model": config.model_name},
            )
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    status=200,
                    headers={"HX-Redirect": reverse("audit-model-settings")},
                )
            return SkylinxRedirect(request)
    else:
        form = AuditModelFieldsForm(
            initial={"fields_to_track": config.tracked_fields or []},
            app_label=config.app_label,
            model_name=config.model_name,
        )

    return render(
        request,
        "skylinx_audit/audit_model_fields_form.html",
        {"form": form, "config": config},
    )


@login_required
@permission_required("skylinx_audit.view_auditmodelconfig")
def activity_log(request):
    """
    Company-wide activity log: aggregates recent history entries from all
    django-simple-history tracked models that are registered in AuditModelConfig.

    Query params:
      ?q=<search>         filter by actor username or model name
      ?page=<n>           pagination
    """
    from django.apps import apps as django_apps

    search_query = request.GET.get("q", "").strip()
    all_history = []

    configs = AuditModelConfig.objects.filter(is_enabled=True).order_by(
        "app_label", "model_name"
    )

    for config in configs:
        try:
            model_cls = django_apps.get_model(config.app_label, config.model_name)
        except LookupError:
            continue

        # django-simple-history attaches a `history` manager to tracked models
        history_manager = getattr(model_cls, "history", None)
        if history_manager is None:
            continue

        qs = history_manager.all().select_related("history_user").order_by(
            "-history_date"
        )[:200]  # cap per model to keep queries fast

        for entry in qs:
            entry._model_label = f"{config.app_label}.{config.model_name}"
            entry._model_verbose = getattr(model_cls._meta, "verbose_name", config.model_name).title()
            all_history.append(entry)

    # Sort combined list by date descending
    all_history.sort(key=lambda e: e.history_date, reverse=True)

    # Search filter (actor username or model name)
    if search_query:
        filtered = []
        sq_lower = search_query.lower()
        for entry in all_history:
            actor = getattr(entry, "history_user", None)
            actor_name = str(actor) if actor else ""
            if (
                sq_lower in actor_name.lower()
                or sq_lower in getattr(entry, "_model_verbose", "").lower()
                or sq_lower in str(getattr(entry, "history_type", "")).lower()
            ):
                filtered.append(entry)
        all_history = filtered

    paginator = Paginator(all_history, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_count": len(all_history),
    }
    return render(request, "skylinx_audit/activity_log.html", context)

