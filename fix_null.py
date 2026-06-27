import os
import re

files_to_fix = ['attendance/models.py', 'asset/models.py', 'recruitment/models.py']
for f in files_to_fix:
    if os.path.exists(f):
        content = open(f, encoding='utf-8').read()
        content = content.replace('on_delete=models.SET_NULL, null=True,\n        null=True,', 'on_delete=models.SET_NULL, null=True,')
        open(f, 'w', encoding='utf-8').write(content)
print('Fixed syntax error')
