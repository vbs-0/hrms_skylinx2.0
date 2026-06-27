import os
import re

# 1. Fix timezone crashes
files_to_fix = ['attendance/filters.py', 'attendance/forms.py']
for f in files_to_fix:
    if os.path.exists(f):
        content = open(f, encoding='utf-8').read()
        content = content.replace('datetime.timezone.now()', 'timezone.now()')
        if 'from django.utils import timezone' not in content:
            content = 'from django.utils import timezone\n' + content
        open(f, 'w', encoding='utf-8').write(content)

# 2. Fix float conversions in payroll
for file in ['payroll/methods/deductions.py', 'payroll/methods/methods.py', 'payroll/methods/payslip_calc.py', 'payroll/methods/tax_calc.py']:
    if os.path.exists(file):
        content = open(file, encoding='utf-8').read()
        # Replace float(...) with Decimal(str(...)) safely
        # Note: We need Decimal imported.
        if 'from decimal import Decimal' not in content:
            content = 'from decimal import Decimal\n' + content
        
        # Simple string replacement for known patterns or regex
        content = re.sub(r'float\((.*?)\)', r'Decimal(str(\1) or "0")', content)
        
        open(file, 'w', encoding='utf-8').write(content)

print('Timezone and Float fixes applied.')
