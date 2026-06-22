import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("attendance/views/views.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = re.findall(r"def\s+work_records\s*\(.*?\):.*?(?=def\s+|\Z)", content, re.DOTALL)
for m in matches:
    print(m)
