import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
from base.skylinx_company_manager import SkylinxCompanyManager
from skylinx.models import SkylinxModel

bad_models = []
for m in apps.get_models():
    if issubclass(m, SkylinxModel):
        filter_path = None
        has_manager = isinstance(m.objects, SkylinxCompanyManager)
        if has_manager:
            try:
                filter_path = m.objects.get_company_filter_path()
            except Exception as e:
                pass
                
        if not filter_path:
            # We skip base.Company because company_id inside Company makes no sense (it's the company itself)
            if m._meta.object_name == 'Company' and m._meta.app_label == 'base':
                continue
            bad_models.append({
                'app': m._meta.app_label,
                'model': m._meta.object_name,
                'has_manager': has_manager,
                'file': m.__module__.replace('.', '/') + '.py'
            })

def ensure_import(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "from base.skylinx_company_manager import SkylinxCompanyManager" not in content:
        # Find where to put it
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('from django.db import models') or line.startswith('from django'):
                lines.insert(i+1, "from base.skylinx_company_manager import SkylinxCompanyManager")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                break

print("Bad models found:")
for b in bad_models:
    print(f"  {b['app']}.{b['model']} (manager: {b['has_manager']})")
print("\n")

for b in bad_models:
    filepath = b['file']
    # It might be in a package like payroll/models/tax_models.py, __module__ is payroll.models.tax_models
    # We can try to open it
    full_path = os.path.join(os.getcwd(), filepath)
    if not os.path.exists(full_path):
        # Could be __init__.py
        full_path = full_path.replace('.py', '/__init__.py')
        if not os.path.exists(full_path):
            print(f"Could not find file for {b['model']}: {filepath}")
            continue
            
    ensure_import(full_path)
    
    with open(full_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_class = False
    class_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^class ' + b['model'] + r'\(', line):
            in_class = True
            class_start = i
            break
            
    if in_class:
        # Find the end of the class signature (e.g. if it spans multiple lines)
        insert_idx = class_start + 1
        while insert_idx < len(lines) and not lines[insert_idx-1].strip().endswith(':'):
            insert_idx += 1
            
        # Check if there is a docstring right after
        while insert_idx < len(lines):
            stripped = lines[insert_idx].strip()
            if not stripped:
                insert_idx += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                # find end of docstring
                if stripped == '"""' or stripped == "'''" or stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                        insert_idx += 1
                        break
                # multi line docstring
                insert_idx += 1
                while insert_idx < len(lines):
                    if '"""' in lines[insert_idx] or "'''" in lines[insert_idx]:
                        insert_idx += 1
                        break
                    insert_idx += 1
                break
            else:
                break
                
        # Insert the code
        # Check if it already has company_id
        has_company = False
        has_mgr = b['has_manager']
        for line in lines[class_start:insert_idx+10]:
            if 'company_id =' in line:
                has_company = True
            if 'objects = SkylinxCompanyManager' in line:
                has_mgr = True
                
        insert_str = ""
        if not has_company:
            insert_str += '    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)\n'
        if not has_mgr:
            insert_str += '    objects = SkylinxCompanyManager()\n'
            
        if insert_str:
            lines.insert(insert_idx, "\n" + insert_str)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"Patched {b['model']} in {filepath}")
        else:
            print(f"Already patched {b['model']} in {filepath}")
