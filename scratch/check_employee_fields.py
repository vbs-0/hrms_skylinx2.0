import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from employee.models import Employee
print("Employee fields related to User:")
for field in Employee._meta.get_fields():
    if field.is_relation and field.related_model:
        print(f"- {field.name}: related to {field.related_model.__name__}")
