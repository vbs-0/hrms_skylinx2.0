"""
Script to fix permission gates across the app.
1. Add filtersubordinates to employee/views.py 
2. Fix attendance/views/requests.py permission gates
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

# === Fix 1: employee/views.py - add filtersubordinates import ===
print("=== Fix 1: employee/views.py imports ===")
with open('employee/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = "    choosesubordinates,"
new_import = "    choosesubordinates,\n    filtersubordinates,"
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print("Added filtersubordinates import")
else:
    print("Import pattern not found - checking manually")
    idx = content.find("choosesubordinates")
    if idx >= 0:
        print(repr(content[idx-20:idx+50]))

with open('employee/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

# === Fix 2: employee/views.py - add filtersubordinates to employee_view ===
print("\n=== Fix 2: employee_view subordinate filtering ===")
# Find the line after base_qs.filter() and before filter_obj
old_view = """    queryset = base_qs.filter()
    filter_obj = EmployeeFilter(request.GET, queryset=queryset).qs"""
new_view = """    queryset = base_qs.filter()
    queryset = filtersubordinates(request, queryset, "employee.change_employee")
    filter_obj = EmployeeFilter(request.GET, queryset=queryset).qs"""
if old_view in content:
    content = content.replace(old_view, new_view, 1)
    print("Added filtersubordinates to employee_view")
else:
    print("employee_view pattern not found")

with open('employee/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

# === Fix 3: attendance/views/requests.py - change permission gates ===
print("\n=== Fix 3: attendance/views/requests.py ===")
with open('attendance/views/requests.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix both filtersubordinates calls
old_perm = 'perm="attendance.view_attendance"'
new_perm = 'perm="employee.change_employee"'
count = content.count(old_perm)
if count > 0:
    content = content.replace(old_perm, new_perm)
    print(f"Replaced {count} occurrence(s) of attendance.view_attendance perm")
else:
    print("Permission pattern not found in requests.py")

with open('attendance/views/requests.py', 'w', encoding='utf-8') as f:
    f.write(content)

# === Verify syntax ===
print("\n=== Verification ===")
try:
    compile(open('employee/views.py', encoding='utf-8').read(), 'employee/views.py', 'exec')
    print("employee/views.py: syntax OK")
except SyntaxError as e:
    print(f"employee/views.py: SYNTAX ERROR: {e}")

try:
    compile(open('attendance/views/requests.py', encoding='utf-8').read(), 'attendance/views/requests.py', 'exec')
    print("attendance/views/requests.py: syntax OK")
except SyntaxError as e:
    print(f"attendance/views/requests.py: SYNTAX ERROR: {e}")

print("\nAll fixes applied!")
