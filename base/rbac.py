"""
Per-tenant RBAC helpers.

Django's auth `Group` is global (no company). For a multi-tenant SaaS each client
must own its own user groups/roles. We keep Django's Group + permission machinery
(so `has_perm` etc. keep working) and add ownership via `base.CompanyGroup`, plus
scope every group query to the requesting user's company. Group names are stored
prefixed (`c<company_id>::<label>`) so two tenants can both have e.g. an "HR"
group; the prefix is stripped for display (see base.apps).
"""
SEP = "::"

def is_platform_owner(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.is_superuser
        and user.username == "skylinx"
    )


def strip_name(name: str) -> str:
    """Display label without the tenant prefix."""
    return name.split(SEP, 1)[-1] if name else name


def scoped_name(company_id, label: str) -> str:
    """Storage name for a group: tenant prefix + bare label."""
    return f"c{company_id}{SEP}{strip_name(label or '').strip()}"


def current_company(request):
    """The Company the request is acting in, or None (superuser/platform)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    # ponytail: memoize per request — called many times per page (rbac, gating,
    # branding); the company can't change mid-request.
    cached = getattr(request, "_current_company", False)
    if cached is not False:
        return cached
    emp = getattr(user, "employee_get", None)
    company = None
    if is_platform_owner(user):
        selected_company = getattr(request, "session", {}).get("selected_company")
        if selected_company and selected_company != "all":
            from base.models import Company

            company = Company.objects.filter(id=selected_company).first()
    elif emp:
        try:
            company = emp.get_company()
        except Exception:
            company = None
    try:
        request._current_company = company
    except Exception:
        pass
    return company


def groups_for_request(request):
    """Groups visible to this request: all for superuser, else this tenant's."""
    from django.contrib.auth.models import Group

    company = current_company(request)
    if is_platform_owner(request.user) and company is None:
        return Group.objects.all()
    if not company:
        return Group.objects.none()
    return Group.objects.filter(company_link__company=company)


def owns_group(request, group_id) -> bool:
    """True if the request may manage this group."""
    from base.models import CompanyGroup

    company = current_company(request)
    if is_platform_owner(request.user) and company is None:
        return True
    if not company:
        return False
    return CompanyGroup.objects.filter(group_id=group_id, company=company).exists()
