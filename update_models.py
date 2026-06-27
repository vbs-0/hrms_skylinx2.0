import os
import re

models_to_update = {
    'payroll/models/models.py': ['ReimbursementMultipleAttachment', 'ReimbursementFile'],
    'pms/models.py': ['AnonymousFeedback'],
    'skylinx_dbtemplate/models.py': ['Template'],
    'attendance/models.py': ['MobileAttendanceDetail', 'MobileLocationLog']
}

for file_path, class_names in models_to_update.items():
    if not os.path.exists(file_path): continue
    content = open(file_path, encoding='utf-8').read()
    
    for cls_name in class_names:
        pattern = re.compile(r'(class ' + cls_name + r'\(.*?\):.*?)(objects = models\.Manager\(\))', re.DOTALL)
        replacement = r'\1objects = SkylinxCompanyManager()\n    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)'
        content = pattern.sub(replacement, content)
        
    open(file_path, 'w', encoding='utf-8').write(content)
print('Done updating models')
