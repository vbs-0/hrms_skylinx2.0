"""Fix all filtersubordinates calls in attendance/views/views.py"""
with open('attendance/views/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all 4 instances where attendance.view_attendance is used as a filtersubordinates perm
# The three in attendance_view (lines 381-392) and the one in another function (line 1192)
old = '"attendance.view_attendance"'
new = '"employee.change_employee"'

count = content.count(old)
print(f"Found {count} occurrences of attendance.view_attendance total")

# Only replace in filtersubordinates context (not in @permission_required decorators etc.)
# By replacing all, we risk changing decorators too. Let me be more specific.

# Read the specific contexts
import re

matches = list(re.finditer(r'filtersubordinates\([^)]*?"attendance\.view_attendance"[^)]*?\)', content, re.DOTALL))
print(f"Found {len(matches)} filtersubordinates calls with attendance.view_attendance")

for i, m in enumerate(matches):
    print(f"  Match {i+1}: {m.group()[:80]}...")

# Replace only the filtersubordinates calls
# These are the specific patterns:
patterns = [
    'filtersubordinates(\n        request, filter_obj.qs, "attendance.view_attendance"\n    )',
    'filtersubordinates(\n        request, validate_attendances, "attendance.view_attendance"\n    )',
    'filtersubordinates(\n        request, ot_attendances, "attendance.view_attendance"\n    )',
    'filtersubordinates(\n        request, total_attendances, "attendance.view_attendance"\n    )',
]

with open('attendance/views/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

for pattern in patterns:
    replacement = pattern.replace('"attendance.view_attendance"', '"employee.change_employee"')
    c = content.count(pattern)
    if c > 0:
        content = content.replace(pattern, replacement)
        print(f"Fixed: {pattern[:60]}...")

with open('attendance/views/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerification:")
remaining = content.count('"attendance.view_attendance"')
print(f"Remaining attendance.view_attendance references: {remaining}")

try:
    compile(content, 'attendance/views/views.py', 'exec')
    print("Syntax: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")
