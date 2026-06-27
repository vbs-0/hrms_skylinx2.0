import os
import re

files_to_update = {
    'attendance/models.py': [
        (r'(employee_id = models\.ForeignKey\(\s*Employee,\s*on_delete=models\.)CASCADE', r'\1SET_NULL, null=True')
    ],
    'asset/models.py': [
        (r'(asset_id = models\.ForeignKey\(\s*Asset,\s*on_delete=models\.)CASCADE', r'\1SET_NULL, null=True'),
        (r'(assigned_to_employee_id = models\.ForeignKey\(\s*Employee,\s*on_delete=models\.)CASCADE', r'\1SET_NULL, null=True')
    ],
    'recruitment/models.py': [
        (r'(stage_id = models\.ForeignKey\(\s*RecruitmentStage,\s*on_delete=models\.)CASCADE', r'\1SET_NULL, null=True')
    ]
}

for file_path, patterns in files_to_update.items():
    if not os.path.exists(file_path): continue
    content = open(file_path, encoding='utf-8').read()
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
        
    open(file_path, 'w', encoding='utf-8').write(content)
print('Done updating CASCADE to SET_NULL')
