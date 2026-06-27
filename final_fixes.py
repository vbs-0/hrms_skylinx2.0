import os
import re

# Fix timezone.now() -> timezone.now()
for root, dirs, files in os.walk('.'):
    if '.git' in root or 'venv' in root or 'migrations' in root: continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'timezone.now()' in content:
                content = content.replace('timezone.now()', 'timezone.now()')
                if 'from django.utils import timezone' not in content:
                    content = 'from django.utils import timezone\n' + content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

# Fix ThreadLocalMiddleware cleanup
middleware_path = 'skylinx/skylinx_middlewares.py'
if os.path.exists(middleware_path):
    with open(middleware_path, 'r', encoding='utf-8') as f:
        mw = f.read()
    if '_thread_locals.request = None' not in mw:
        mw = re.sub(r'(def __call__\(self, request\):.*?return response)', r'\1\n        _thread_locals.request = None', mw, flags=re.DOTALL)
        with open(middleware_path, 'w', encoding='utf-8') as f:
            f.write(mw)

# Fix WorkRecords import in payroll
payroll_models = 'payroll/models/models.py'
if os.path.exists(payroll_models):
    with open(payroll_models, 'r', encoding='utf-8') as f:
        pm = f.read()
    pm = re.sub(r'class WorkRecord\(models\.Model\):.*?(?=class )', '', pm, flags=re.DOTALL)
    if 'from attendance.models import WorkRecords' not in pm:
        pm = 'from attendance.models import WorkRecords\n' + pm
    pm = pm.replace('WorkRecord', 'WorkRecords')
    with open(payroll_models, 'w', encoding='utf-8') as f:
        f.write(pm)
print('Done executing final fixes')
