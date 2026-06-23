import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from base.forms import AssignUserGroup
from employee.models import Employee
from django.contrib.auth.models import Group

groups = Group.objects.all()
print("Groups:", groups.count())
for g in groups[:3]:
    users = g.user_set.all()
    emps = Employee.objects.filter(employee_user_id__groups__id=g.id)
    print("  Group", g.name, ":", users.count(), "users,", emps.count(), "employees")
    emp_ids = list(emps.values_list('id', flat=True))
    print("    Employee IDs:", emp_ids[:5])

    # Test creating the form with initial - same as the view does
    form = AssignUserGroup(
        initial={
            'group': g.id,
            'employee': Employee.objects.filter(
                employee_user_id__groups__id=g.id
            ).values_list('id', flat=True),
        }
    )
    init_val = form.initial.get('employee', [])
    print("    Form initial employee:", list(init_val)[:5])
    widget_val = form['employee'].value()
    print("    Widget value:", widget_val[:5] if widget_val else widget_val)
    print("    Widget value type:", type(widget_val))
