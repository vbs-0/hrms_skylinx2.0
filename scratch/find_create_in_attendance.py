import os
import re

def search_attendance_creates(root_dir):
    matches = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if 'create' in line.lower() and ('oh-btn' in line or 'button' in line or 'href=' in line or 'a ' in line):
                                matches.append((filepath, line_num, line.strip()))
                except Exception:
                    pass
    return matches

results = search_attendance_creates("attendance/templates")
print(f"Found {len(results)} matches for create elements in attendance templates:")
for r in results:
    print(f"- {r[0]}:{r[1]}: {r[2]}")
