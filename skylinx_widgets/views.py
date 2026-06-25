from django.shortcuts import render

from skylinx.decorators import login_required
from skylinx_widgets.widgets.select_widgets import (
    ALL_INSTANCES,
    SkylinxMultiSelectWidget,
)

# Create your views here.

# urls.py
# path("employee-widget-filter",views.widget_filter,name="employee-widget-filter")

# views.py
# @login_required
# def widget_filter(request):
#     """
#     This method is used to return all the ids of the employees
#     """
#     ids = EmployeeFilter(request.GET).qs.values_list("id", flat=True)
#     return JsonResponse({'ids':list(ids)})


from django.http import HttpResponse

@login_required
def get_filter_form(request):
    """
    This method will return filtering from
    """
    try:
        widget_instance = ALL_INSTANCES.get(str(request.user.id))
        if not widget_instance:
            return HttpResponse("")
        template_path = request.GET.get("template_path")
        if not template_path:
            return HttpResponse("")
        return render(request, template_path, {"f": widget_instance.filter_class()})
    except Exception:
        return HttpResponse("")
