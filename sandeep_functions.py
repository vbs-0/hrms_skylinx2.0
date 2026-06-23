# Function: home
def home(request):
    """
    Renders the Home Page ΓÇö a visual launchpad showing all module navigation cards.
    """
    if not request.user.is_authenticated:
        return redirect("login")

    from django.apps import apps

    def get_count_or_zero(app_label, model_name, filter_kwargs=None):
        try:
            model = apps.get_model(app_label, model_name)
            if filter_kwargs:
                return model.objects.filter(**filter_kwargs).count()
            return model.objects.count()
        except Exception:
            return 0

    pending_leaves_count = get_count_or_zero('leave', 'LeaveRequest', {'status': 'requested'})
    onboarding_candidates_count = get_count_or_zero('onboarding', 'OnboardingCandidate')

    employee_add_alert = onboarding_candidates_count > 0
    is_payroll_time = get_count_or_zero('payroll', 'Payslip') == 0

    unread_notifications_count = 0
    try:
        unread_notifications_count = request.user.notifications.unread().count()
    except Exception:
        pass

    tasks_active = (pending_leaves_count > 0) or employee_add_alert or (unread_notifications_count > 0) or is_payroll_time

    context = {
        "pending_leaves_count": pending_leaves_count,
        "employee_add_alert": employee_add_alert,
        "is_payroll_time": is_payroll_time,
        "unread_notifications_count": unread_notifications_count,
        "tasks_active": tasks_active,
    }

    return render(request, "home_page.html", context)
----------------------------------------
# Function: dashboard_components_toggle
def dashboard_components_toggle(request):
    """
    This function is used to create personalized dashboard charts for employees
    """
    employee_charts, created = DashboardEmployeeCharts.objects.get_or_create(
        employee=request.user.employee_get
    )
    charts = employee_charts.charts or []
    chart_id = request.GET.get("chart_id")
    if chart_id and chart_id in charts:
        charts.remove(chart_id)
        employee_charts.charts = charts
        employee_charts.save()
    return HttpResponse("")
----------------------------------------
