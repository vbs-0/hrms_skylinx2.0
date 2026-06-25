def holiday_calendar_view(request):
    """
    Renders a unified Holiday Calendar containing public holidays and approved leaves.
    Supports year/month selection and AJAX/HTMX sub-rendering.
    """
    import calendar
    from datetime import date, timedelta
    from django.db.models import Q
    from base.models import Holidays
    from leave.models import LeaveRequest

    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    # Clamp year/month
    if not (1 <= month <= 12):
        month = today.month
    if year < 1970 or year > 2100:
        year = today.year

    # Calculate month bounds
    first_weekday, num_days = calendar.monthrange(year, month)

    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    # Holidays in this range
    holidays = Holidays.objects.filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    )

    # Approved leaves in this range
    leaves_qs = LeaveRequest.objects.filter(
        status="approved",
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if not request.user.is_superuser and not request.user.has_perm("leave.view_leaverequest"):
        # Regular user: only show his/her own leaves
        employee = getattr(request.user, "employee_get", None)
        if employee:
            leaves_qs = leaves_qs.filter(employee_id=employee)
        else:
            leaves_qs = leaves_qs.none()

    leaves = leaves_qs.select_related("employee_id", "leave_type_id")

    # Map events to day number
    events_by_day = {}
    for h in holidays:
        curr = max(h.start_date, start_date)
        end = min(h.end_date or h.start_date, end_date)
        while curr <= end:
            events_by_day.setdefault(curr.day, []).append({
                "type": "holiday",
                "name": h.name,
            })
            curr += timedelta(days=1)

    for l in leaves:
        curr = max(l.start_date, start_date)
        end = min(l.end_date, end_date)
        while curr <= end:
            events_by_day.setdefault(curr.day, []).append({
                "type": "leave",
                "employee": l.employee_id.get_full_name() if l.employee_id else "Employee",
                "leave_type": l.leave_type_id.name if l.leave_type_id else "Leave",
            })
            curr += timedelta(days=1)

    # Build calendar day list
    weeks = []
    current_week = []
    
    # Pad start of month (0=Mon, ..., 6=Sun)
    for _ in range(first_weekday):
        current_week.append({"day": "", "events": [], "is_weekend": False})

    for day in range(1, num_days + 1):
        cur_date = date(year, month, day)
        day_of_week = cur_date.weekday()
        is_weekend = day_of_week >= 5

        current_week.append({
            "day": day,
            "date": cur_date.isoformat(),
            "events": events_by_day.get(day, []),
            "is_weekend": is_weekend,
            "is_today": (cur_date == today),
        })

        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

    # Pad end of month
    if current_week:
        while len(current_week) < 7:
            current_week.append({"day": "", "events": [], "is_weekend": False})
        weeks.append(current_week)

    # Next/Prev navigation
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    month_name = calendar.month_name[month]

    dashboard = (request.GET.get("dashboard") == "1")
    context = {
        "weeks": weeks,
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": today,
        "holidays_list": holidays,
        "leaves_list": leaves,
        "show_list": not dashboard,
        "extra_params": "&dashboard=1" if dashboard else "",
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("hx") == "1":
        return render(request, "holiday_calendar_fragment.html", context)

    return render(request, "holiday_calendar.html", context)




