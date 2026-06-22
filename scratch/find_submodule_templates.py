import os
import re

def search_templates_in_views(root_dir):
    matches = []
    # Search for view definitions or templates rendered
    for root, dirs, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Search for def work_records, view_my_attendance, attendance_activity_view, etc.
                        # and find '.html' inside those views
                        funcs = re.findall(r"def\s+(work_records|view_my_attendance|attendance_activity_view|attendance_activity)[^:]+:(.*?)(?=def\s+|\Z)", content, re.DOTALL)
                        for f_name, f_body in funcs:
                            templates = re.findall(r"['\"][^'\"]+\.html['\"]", f_body)
                            matches.append((filepath, f_name, templates))
                except Exception as e:
                    print(e)
    return matches

results = search_templates_in_views("attendance")
print("Found rendered templates in views:")
for r in results:
    print(f"- File: {r[0]}, View: {r[1]}, Templates: {r[2]}")
