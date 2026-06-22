import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("attendance/cbv/hour_account.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for references to templates or get_context_data
for line_num, line in enumerate(content.split('\n'), 1):
    if 'nav_hour_account.html' in line or 'create_attrs' in line or 'template_name' in line:
        print(f"Line {line_num}: {line.strip()}")
