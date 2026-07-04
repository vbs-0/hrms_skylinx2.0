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
    # The platform owner is the superuser. Tenants are always non-superuser
    # Company Admins, so is_superuser is the operator marker. (Was hardcoded to
    # username=="skylinx", which broke when the owner was renamed to "emplinx".)
    return bool(user and user.is_authenticated and user.is_superuser)


def hierarchy_rank(user) -> int:
    """Tenant hierarchy tier (lower = higher authority).

    0 = platform owner, 1 = client admin / CEO (Company Admin group),
    2 = HR Manager, 3 = everyone else (Manager / Employee).

    Used to hide higher-tier people and their requests from lower tiers:
    the CEO is invisible to HR + employees, HR is invisible to employees.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return 3
    if is_platform_owner(user):
        return 0
    # cache per user object — called per row when scoping lists
    cached = getattr(user, "_hierarchy_rank", None)
    if cached is not None:
        return cached
    names = set(user.groups.values_list("name", flat=True))
    if "Company Admin" in names:
        rank = 1
    elif any(n.endswith(SEP + "HR Manager") for n in names):
        rank = 2
    else:
        rank = 3
    try:
        user._hierarchy_rank = rank
    except Exception:
        pass
    return rank


def higher_tier_user_ids(viewer):
    """User ids strictly above ``viewer`` in the hierarchy (to exclude from lists).

    A CEO (rank 1) sees everyone below. An HR Manager (rank 2) must not see the
    CEO. An employee (rank 3) must not see CEO or HR.
    """
    from django.contrib.auth.models import Group

    viewer_rank = hierarchy_rank(viewer)
    if viewer_rank <= 1:  # owner / CEO see everyone
        return []
    names = []
    if viewer_rank >= 2:  # below CEO -> hide CEO
        names.append("Company Admin")
    ids = set(
        Group.objects.filter(name__in=names).values_list(
            "user__id", flat=True
        )
    )
    if viewer_rank >= 3:  # plain employee -> also hide HR Managers
        ids |= set(
            Group.objects.filter(name__endswith=SEP + "HR Manager").values_list(
                "user__id", flat=True
            )
        )
    ids.discard(None)
    ids.discard(getattr(viewer, "id", None))  # never hide self
    return list(ids)


def exclude_higher_tier(request, queryset, user_path="employee_id__employee_user_id"):
    """Drop rows whose owning user outranks the viewer.

    Mirrors the employee-directory rule for request lists: a CEO's requests are
    hidden from HR + employees, an HR's from employees. ``user_path`` is the ORM
    path from the row to the owning auth user. No-op for CEO/owner viewers.
    """
    user = getattr(request, "user", None)
    if user is None:
        return queryset
    hidden = higher_tier_user_ids(user)
    if hidden:
        queryset = queryset.exclude(**{f"{user_path}__id__in": hidden})
    return queryset


# Org-chart eligibility: who is allowed to be picked as someone's reporting
# manager. Finer-grained than hierarchy_rank() above (splits Manager out from
# plain Employee) so an Employee can report to a Manager, a Manager to an HR
# Manager, an HR Manager to the CEO, and the CEO to no one.
CEO_RANK, HR_MANAGER_RANK, MANAGER_RANK, EMPLOYEE_RANK = 1, 2, 3, 4


def org_rank(user) -> int:
    """4-tier rank for reporting-manager eligibility (lower = more senior)."""
    if not user or not getattr(user, "is_authenticated", False):
        return EMPLOYEE_RANK
    if is_platform_owner(user):
        return 0
    names = set(user.groups.values_list("name", flat=True))
    if "Company Admin" in names:
        return CEO_RANK
    if any(n.endswith(SEP + "HR Manager") for n in names):
        return HR_MANAGER_RANK
    if any(n.endswith(SEP + "Manager") for n in names):
        return MANAGER_RANK
    return EMPLOYEE_RANK


def senior_user_ids(target_user):
    """User ids strictly more senior than ``target_user`` — valid reporting-manager
    candidates. A brand-new employee (target_user=None) defaults to the lowest
    tier, so every existing role outranks them."""
    from django.contrib.auth.models import Group

    target_rank = org_rank(target_user) if target_user else EMPLOYEE_RANK
    if target_rank <= CEO_RANK:
        return []  # CEO/owner: no one outranks them
    ids = set(
        Group.objects.filter(name="Company Admin").values_list("user__id", flat=True)
    )
    if target_rank > HR_MANAGER_RANK:
        ids |= set(
            Group.objects.filter(name__endswith=SEP + "HR Manager").values_list(
                "user__id", flat=True
            )
        )
    if target_rank > MANAGER_RANK:
        ids |= set(
            Group.objects.filter(name__endswith=SEP + "Manager").values_list(
                "user__id", flat=True
            )
        )
    ids.discard(None)
    return list(ids)


def manager_candidate_user_ids(target_user):
    """Who may be picked as ``target_user``'s reporting manager.

    CEO: no one. HR Manager: only CEO or other HR Managers (never a plain
    employee). Manager/Employee: anyone, peers included (HR decides).
    Returns None to mean "no restriction".
    """
    from django.contrib.auth.models import Group

    target_rank = org_rank(target_user) if target_user else EMPLOYEE_RANK
    if target_rank <= CEO_RANK:
        return []
    if target_rank == HR_MANAGER_RANK:
        ids = set(
            Group.objects.filter(name="Company Admin").values_list("user__id", flat=True)
        ) | set(
            Group.objects.filter(name__endswith=SEP + "HR Manager").values_list(
                "user__id", flat=True
            )
        )
        ids.discard(None)
        ids.discard(getattr(target_user, "id", None))
        return list(ids)
    return None


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
