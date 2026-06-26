#!/usr/bin/env python
"""
Comprehensive fix for all remaining vulnerable permission gates.
Replaces view-level permissions with change-level permissions where
regular employees would bypass subordinate filtering.
"""
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

REPLACEMENTS = [
    # =========================================================================
    # employee/views.py (already mostly fixed, check remaining)
    # =========================================================================

    # =========================================================================
    # base/views.py - global_search function
    # =========================================================================
    {
        "file": "base/views.py",
        "old": 'if request.user.has_perm("employee.view_employee"):',
        "new": 'if request.user.has_perm("employee.change_employee"):',
        "count": 0,
    },
    {
        "file": "base/views.py",
        "old": 'request, employees, perm="employee.view_employee"',
        "new": 'request, employees, perm="employee.change_employee"',
        "count": 0,
    },

    # =========================================================================
    # base/dashboard.py - analytics permission gates
    # =========================================================================
    {
        "file": "base/dashboard.py",
        "old": 'def can_view_company_analytics(user, perm="employee.view_employee"):',
        "new": 'def can_view_company_analytics(user, perm="employee.change_employee"):',
        "count": 0,
    },
    {
        "file": "base/dashboard.py",
        "old": 'def analytics_permission_required(perm="employee.view_employee"):',
        "new": 'def analytics_permission_required(perm="employee.change_employee"):',
        "count": 0,
    },
    {
        "file": "base/dashboard.py",
        "old": '@analytics_permission_required("attendance.view_attendance")',
        "new": '@analytics_permission_required("employee.change_employee")',
        "count": 0,
    },
    {
        "file": "base/dashboard.py",
        "old": '@analytics_permission_required("employee.view_employee")',
        "new": '@analytics_permission_required("employee.change_employee")',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # base/methods.py - CHART_CONFIG
    # =========================================================================
    {
        "file": "base/methods.py",
        "old": '"perm": "employee.view_employee",',
        "new": '"perm": "employee.change_employee",',
        "count": 0,
        "multi": True,
    },
    {
        "file": "base/methods.py",
        "old": '"perm": "attendance.view_attendance",',
        "new": '"perm": "employee.change_employee",',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # base/cbv/mail_log_tab.py
    # =========================================================================
    {
        "file": "base/cbv/mail_log_tab.py",
        "old": 'perm="employee.view_employee",',
        "new": 'perm="employee.change_employee",',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # employee/cbv/employees.py
    # =========================================================================
    {
        "file": "employee/cbv/employees.py",
        "old": 'perm="employee.view_employee",',
        "new": 'perm="employee.change_employee",',
        "count": 0,
        "multi": True,
    },
    {
        "file": "employee/cbv/employees.py",
        "old": '"employee.view_employee"',
        "new": '"employee.change_employee"',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # employee/cbv/accessibility.py - mail_log_accessibility
    # =========================================================================
    {
        "file": "employee/cbv/accessibility.py",
        "old": '"employee.view_employee"',
        "new": '"employee.change_employee"',
        "count": 0,
        "multi": False,
    },
    # Only change mail_log_accessibility, not the other functions
    # Let me be more specific
    {
        "file": "employee/cbv/accessibility.py",
        "old": 'if request.user.has_perm("employee.change_employee"):\n        return True\n    return False\n\n\ndef note_accessibility',
        "new": 'if request.user.has_perm("employee.change_employee"):\n        return True\n    return False\n\n\ndef note_accessibility',
        "count": 0,
    },
    # This one we need to be more careful with

    # =========================================================================
    # report/views/employee_report.py
    # =========================================================================
    {
        "file": "report/views/employee_report.py",
        "old": '@permission_required(perm="employee.view_employee")',
        "new": '@permission_required(perm="employee.change_employee")',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # report/views/attendance_report.py
    # =========================================================================
    {
        "file": "report/views/attendance_report.py",
        "old": '@permission_required(perm="attendance.view_attendance")',
        "new": '@permission_required(perm="employee.change_employee")',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # report/sidebar.py
    # =========================================================================
    {
        "file": "report/sidebar.py",
        "old": 'or request.user.has_perm("employee.view_employee")',
        "new": 'or request.user.has_perm("employee.change_employee")',
        "count": 0,
    },
    {
        "file": "report/sidebar.py",
        "old": 'or request.user.has_perm("attendance.view_attendance")',
        "new": 'or request.user.has_perm("employee.change_employee")',
        "count": 0,
    },
    {
        "file": "report/sidebar.py",
        "old": 'return request.user.is_superuser or request.user.has_perm("employee.view_employee")',
        "new": 'return request.user.is_superuser or request.user.has_perm("employee.change_employee")',
        "count": 0,
    },
    {
        "file": "report/sidebar.py",
        "old": 'return request.user.is_superuser or request.user.has_perm(\n        "attendance.view_attendance"\n    )',
        "new": 'return request.user.is_superuser or request.user.has_perm(\n        "employee.change_employee"\n    )',
        "count": 0,
    },
    {
        "file": "report/sidebar.py",
        "old": 'return request.user.is_superuser or request.user.has_perm("employee.change_employee")',
        "new": 'return request.user.is_superuser or request.user.has_perm("employee.change_employee")',
        "count": 0,
    },

    # =========================================================================
    # attendance/sidebar.py
    # =========================================================================
    {
        "file": "attendance/sidebar.py",
        "old": 'return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(',
        "new": 'return request.user.has_perm("employee.change_employee") or is_reportingmanager(',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # attendance/views/requests.py
    # =========================================================================
    {
        "file": "attendance/views/requests.py",
        "old": 'if request.user.has_perm("attendance.view_attendance"):',
        "new": 'if request.user.has_perm("employee.change_employee"):',
        "count": 0,
        "multi": True,
    },
    {
        "file": "attendance/views/requests.py",
        "old": 'request.user.has_perm("attendance.view_attendance")',
        "new": 'request.user.has_perm("employee.change_employee")',
        "count": 0,
    },

    # =========================================================================
    # skylinx_api/api_views/attendance/views.py
    # =========================================================================
    {
        "file": "skylinx_api/api_views/attendance/views.py",
        "old": 'perm = "attendance.view_attendance"',
        "new": 'perm = "employee.change_employee"',
        "count": 0,
    },
    {
        "file": "skylinx_api/api_views/attendance/views.py",
        "old": 'perm="attendance.view_attendance",',
        "new": 'perm="employee.change_employee",',
        "count": 0,
    },
    {
        "file": "skylinx_api/api_views/attendance/views.py",
        "old": 'if user.has_perm("attendance.view_attendance"):',
        "new": 'if user.has_perm("employee.change_employee"):',
        "count": 0,
        "multi": True,
    },
    {
        "file": "skylinx_api/api_views/attendance/views.py",
        "old": 'if request.user.has_perm("employee.view_enployee") or is_manager:',
        "new": 'if request.user.has_perm("employee.change_employee") or is_manager:',
        "count": 0,
    },

    # =========================================================================
    # skylinx_api/api_views/attendance/permission_views.py
    # =========================================================================
    {
        "file": "skylinx_api/api_views/attendance/permission_views.py",
        "old": '"attendance.view_attendance"',
        "new": '"employee.change_employee"',
        "count": 0,
        "multi": True,
    },

    # =========================================================================
    # skylinx_api/api_views/employee/views.py (remaining gates)
    # =========================================================================
    {
        "file": "skylinx_api/api_views/employee/views.py",
        "old": 'if user.has_perm("employee.view_employee"):\n            company = request.META.get("HTTP_COMPANY", None) or request.session.get("selected_company", None)\n            if company and company != "all":\n                if not getattr(employee, "employee_work_info", None) or employee.employee_work_info.company_id.id != int(company):\n                    return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)\n            if employee.employee_user_id.is_superuser:\n                return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)\n            serializer = EmployeeSerializer(employee)\n            return Response(serializer.data)',
        "new": 'if user.has_perm("employee.change_employee"):\n            company = request.META.get("HTTP_COMPANY", None) or request.session.get("selected_company", None)\n            if company and company != "all":\n                if not getattr(employee, "employee_work_info", None) or employee.employee_work_info.company_id.id != int(company):\n                    return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)\n            if employee.employee_user_id.is_superuser:\n                return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)\n            serializer = EmployeeSerializer(employee)\n            return Response(serializer.data)',
        "count": 0,
    },
    {
        "file": "skylinx_api/api_views/employee/views.py",
        "old": 'if user.has_perm("employee.view_employee"):\n            company = request.META.get("HTTP_COMPANY", None) or request.session.get("selected_company", None)\n            if company and company != "all":\n                employees_queryset = employees_queryset.filter(employee_work_info__company_id=company)\n            employees_queryset = employees_queryset.exclude(employee_user_id__is_superuser=True)\n        else:\n            subordinate_qs = user.employee_get.get_subordinate_employees()\n            if subordinate_qs.exists():\n                employees_queryset = subordinate_qs.only(\n                    "id", "employee_first_name", "employee_last_name"\n                )\n            else:\n                employees_queryset = employees_queryset.filter(id=user.employee_get.id)',
        "new": 'if user.has_perm("employee.change_employee"):\n            company = request.META.get("HTTP_COMPANY", None) or request.session.get("selected_company", None)\n            if company and company != "all":\n                employees_queryset = employees_queryset.filter(employee_work_info__company_id=company)\n            employees_queryset = employees_queryset.exclude(employee_user_id__is_superuser=True)\n        else:\n            subordinate_qs = user.employee_get.get_subordinate_employees()\n            if subordinate_qs.exists():\n                employees_queryset = subordinate_qs.only(\n                    "id", "employee_first_name", "employee_last_name"\n                )\n            else:\n                employees_queryset = employees_queryset.filter(id=user.employee_get.id)',
        "count": 0,
    },
    {
        "file": "skylinx_api/api_views/employee/views.py",
        "old": 'if request.user.has_perm("employee.view_employee"):\n            employees = Employee.objects.all()',
        "new": 'if request.user.has_perm("employee.change_employee"):\n            employees = Employee.objects.all()',
        "count": 0,
    },
]

def apply_replacements():
    """Apply all replacements to files."""
    total_changed = 0
    total_files = set()
    
    for r in REPLACEMENTS:
        filepath = r["file"]
        if not os.path.exists(filepath):
            print(f"  SKIP: {filepath} not found")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        old = r["old"]
        new = r["new"]
        multi = r.get("multi", False)
        
        if multi:
            # Replace all occurrences
            new_content = content.replace(old, new)
        else:
            # Replace only first occurrence
            new_content = content.replace(old, new, 1)
        
        if new_content != content:
            count = content.count(old) if multi else 1
            r["count"] = content.count(old)
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(new_content)
            total_changed += r["count"]
            total_files.add(filepath)
            print(f"  OK: {filepath} - {r['count']} occurrence(s) of '{old[:60]}...'")
        else:
            print(f"  --: {filepath} - no match for '{old[:60]}...'")
    
    print(f"\nTotal: {total_changed} replacements across {len(total_files)} files")

def verify_remaining():
    """Check for any remaining vulnerable gates."""
    import subprocess
    
    patterns = [
        ('"employee.view_employee"', 'employee.view_employee'),
        ('"attendance.view_attendance"', 'attendance.view_attendance (exact)'),
    ]
    
    print("\n=== Verifying remaining vulnerable gates ===\n")
    
    # Use grep-style search via Python
    for pattern, name in patterns:
        print(f"--- {name} ---")
        for root, dirs, files in os.walk('.'):
            # Skip unwanted dirs
            if any(x in root for x in ['__pycache__', '.git', 'node_modules', 'venv', 'scripts', 'scratch']):
                continue
            for f in files:
                if not f.endswith('.py'):
                    continue
                if f in ('manage.py', '__init__.py'):
                    continue
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        for i, line in enumerate(fh, 1):
                            if pattern in line:
                                print(f"  {filepath}:{i}: {line.strip()[:100]}")
                except:
                    pass

if __name__ == '__main__':
    apply_replacements()
    verify_remaining()
