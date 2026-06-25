from django.contrib import messages
from django.shortcuts import render

from base.methods import check_manager
from helpdesk.models import Ticket
from skylinx.http.response import SkylinxRedirect

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def ticket_owner_can_enter(function, perm: str, model: object, manager_access=False):
    from employee.models import Employee, EmployeeWorkInformation

    """
    Only the users with permission, or the owner, or employees manager can enter,
    If manager_access:True then all the managers can enter
    """

    def _function(request, *args, **kwargs):
        instance_id = kwargs[list(kwargs.keys())[0]]
        instance = None
        if model == Employee:
            employee = Employee.objects.get(id=instance_id)
        else:
            try:
                instance = model.objects.get(id=instance_id)
                employee = instance.employee_id
            except:
                messages.error(request, ("Sorry, something went wrong!"))
                return SkylinxRedirect(request)

        # Resolve the specific ticket this action targets (if any) so the
        # owner/assignee checks below are scoped to THIS ticket only — never a
        # blanket "owns any ticket" test.
        ticket = instance if isinstance(instance, Ticket) else None
        current_employee = request.user.employee_get

        is_ticket_owner = bool(
            ticket
            and (
                ticket.created_by == request.user
                or current_employee in ticket.assigned_to.all()
            )
        )

        can_enter = (
            current_employee == employee
            or request.user.has_perm(perm)
            or check_manager(current_employee, employee)
            or (
                EmployeeWorkInformation.objects.filter(
                    reporting_manager_id__employee_user_id=request.user
                ).exists()
                if manager_access
                else False
            )
            or is_ticket_owner
        )
        if can_enter:
            return function(request, *args, **kwargs)
        return render(request, "no_perm.html")

    return _function
