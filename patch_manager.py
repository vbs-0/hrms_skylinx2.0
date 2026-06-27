import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
from skylinx.models import SkylinxModel

bad_models = [
    'WorkTypeRequestComment', 'ShiftRequestComment', 'AnnouncementComment',
    'LeaveTypeCondition', 'CompensatoryLeaverequestComment',
    'AssetDocuments', 'TaxBracket', 'AccountBlockUnblock'
]

for m in apps.get_models():
    if m._meta.object_name in bad_models:
        filepath = m.__module__.replace('.', '/') + '.py'
        if not os.path.exists(filepath):
            filepath = filepath.replace('.py', '/__init__.py')
            if not os.path.exists(filepath):
                continue
                
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        in_class = False
        class_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^class ' + m._meta.object_name + r'\(', line):
                in_class = True
                class_start = i
                
            elif in_class and re.match(r'^class ', line):
                in_class = False
                
            if in_class and 'objects = models.Manager()' in line:
                lines[i] = '# ' + line
                
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            print(f"Patched {m._meta.object_name} in {filepath}")
