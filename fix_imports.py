import os
import re

files_to_fix = [
    'skylinx_dbtemplate/models.py', 
    'pms/models.py', 
    'attendance/models.py', 
    'payroll/models/models.py',
    'base/models.py',
    'biometric/models.py'
]
for f in files_to_fix:
    if os.path.exists(f):
        content = open(f, encoding='utf-8').read()
        if 'SkylinxCompanyManager' in content and 'from base.skylinx_company_manager import SkylinxCompanyManager' not in content:
            # Need to avoid circular imports if base/models.py
            if f == 'base/models.py':
                import_stmt = 'from base.skylinx_company_manager import SkylinxCompanyManager\n'
            else:
                import_stmt = 'from base.skylinx_company_manager import SkylinxCompanyManager\n'
            
            if 'import models' in content:
                content = content.replace('from django.db import models', 'from django.db import models\n' + import_stmt)
            else:
                content = import_stmt + content
                
        open(f, 'w', encoding='utf-8').write(content)
print('Fixed imports')
