import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
Contract = apps.get_model('payroll', 'Contract')

print("Contract fields:")
for f in Contract._meta.get_fields():
    if not f.is_relation or f.many_to_one:
        print(f"  {f.name}: {type(f).__name__}")
