"""
Fix all multi-tenancy / role-based access control permission gate bugs.
"""
import os
import sys

REPLACEMENTS = [
    # 1. employee/views.py - change view_employee to change_employee (13x decorator + 5x filtersubordinates)
    ("employee/views.py", "employee.view_employee", "employee.change_employee"),
    # 2. Fix document_request_view
    ("employee/views.py", '"skylinx_documents.view_documentrequest"', '"skylinx_documents.change_documentrequest"'),
    
    # 3. employee/filters.py
    ("employee/filters.py", '"employee.view_employee"', '"employee.change_employee"'),
    
    # 4. employee/not_in_out_dashboard.py
    ("employee/not_in_out_dashboard.py", '"employee.view_employee"', '"employee.change_employee"'),
    
    # 5. attendance/views.py (ROOT level)
    ("attendance/views.py", '"attendance.view_attendance"', '"employee.change_employee"'),
    
    # 6. attendance/cbv/attendances.py
    ("attendance/cbv/attendances.py", '"attendance.view_attendance"', '"employee.change_employee"'),
    
    # 7. attendance/views/search.py
    ("attendance/views/search.py", '"attendance.view_attendance"', '"employee.change_employee"'),
    
    # 8. attendance/cbv/dashboard_offline_online.py (wrong cross-module perm)
    ("attendance/cbv/dashboard_offline_online.py", '"leave.view_leaverequest"', '"employee.change_employee"'),
    
    # 9. attendance/views/views.py - only change employee.view_employee
    ("attendance/views/views.py", 'manager_can_enter("employee.view_employee"', 'manager_can_enter("employee.change_employee"'),
    
    # 10. base/views.py
    ("base/views.py", '"employee.view_employeeworkinformation"', '"employee.change_employee"'),
    
    # 11. base/cbv/dashboard/dashboard.py
    ("base/cbv/dashboard/dashboard.py", '"employee.view_employeeworkinformation"', '"employee.change_employee"'),
    
    # 12. helpdesk/views.py
    ("helpdesk/views.py", '"helpdesk.view_ticket"', '"helpdesk.change_ticket"'),
]

# Exclude files from verification
EXCLUDE_PATTERNS = ['fix_all_permission_gates', 'manage.py', 'migrations', '.pyc']

def apply_replacements(replacements):
    file_changes = {}
    for filepath, old, new in replacements:
        if filepath not in file_changes:
            file_changes[filepath] = []
        file_changes[filepath].append((old, new))

    for filepath, changes in sorted(file_changes.items()):
        if not os.path.exists(filepath):
            print(f"SKIP: {filepath} not found")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        total_replacements = 0
        for old, new in changes:
            count = content.count(old)
            if count > 0:
                content = content.replace(old, new)
                total_replacements += count
                print(f"  OK {filepath}: {count}x '{old}' -> '{new}'")
            else:
                print(f"  XX {filepath}: 0x '{old}' (not found)")

        if total_replacements > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  SAVED {filepath}: {total_replacements} replacement(s)\n")
        else:
            print(f"  SKIP {filepath}: no changes\n")


print("=" * 60)
print("APPLYING PERMISSION GATE FIXES")
print("=" * 60)

apply_replacements(REPLACEMENTS)

print("=" * 60)
print("VERIFICATION")
print("=" * 60)

import subprocess

weak_gates = [
    ('filtersubordinates.*"employee.view_employee"', 'filtersubordinates with employee.view_employee'),
    ('filtersubordinatesemployeemodel.*"employee.view_employee"', 'filtersubordinatesemployeemodel with employee.view_employee'),
    ('manager_can_enter\\("employee.view_employee"\\)', 'manager_can_enter with employee.view_employee'),
    ('manager_can_enter\\("attendance.view_attendance"\\)', 'manager_can_enter with attendance.view_attendance'),
    ('filtersubordinates.*"attendance.view_attendance"', 'filtersubordinates with attendance.view_attendance'),
    ('manager_can_enter\\("employee.view_employeeworkinformation"\\)', 'manager_can_enter with employee.view_employeeworkinformation'),
    ('filtersubordinates.*"employee.view_employeeworkinformation"', 'filtersubordinates with employee.view_employeeworkinformation'),
    ('filtersubordinatesemployeemodel.*"employee.view_employeeworkinformation"', 'filtersubordinatesemployeemodel with employee.view_employeeworkinformation'),
    ('manager_can_enter\\("helpdesk.view_ticket"\\)', 'manager_can_enter with helpdesk.view_ticket'),
    ('filtersubordinates.*"helpdesk.view_ticket"', 'filtersubordinates with helpdesk.view_ticket'),
    ('manager_can_enter\\("leave.view_leaverequest"\\)', 'manager_can_enter with leave.view_leaverequest (in non-leave module)'),
    ('filtersubordinates.*"skylinx_documents.view_documentrequest"', 'filtersubordinates with skylinx_documents.view_documentrequest'),
]

all_clear = True
for pattern, desc in weak_gates:
    try:
        result = subprocess.run(
            ['grep', '-rn', pattern, '--include="*.py"', '.'],
            capture_output=True, text=True, timeout=10,
            cwd='.'
        )
        lines = [l for l in result.stdout.split('\n') if l and not any(e in l for e in EXCLUDE_PATTERNS)]
        if lines:
            print(f"  REMAINING: {desc}")
            for line in lines[:5]:
                print(f"    {line}")
            all_clear = False
    except Exception as e:
        print(f"  grep error: {e}")

if all_clear:
    print("  ALL weak gates have been fixed!")
else:
    print("  Some weak gates still remain (check above)")

print("\nDone!")
