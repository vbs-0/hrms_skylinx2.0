#!/usr/bin/env python
"""
Comprehensive fix for ALL remaining vulnerable permission gates.

Replaces view-level permissions (which regular employees have by default)
with change-level permissions (managers/superusers only).

Patterns:
  employee.view_employee           → employee.change_employee
  employee.view_employeeworkinformation  → employee.change_employee
  attendance.view_attendance       → employee.change_employee
  leave.view_leaverequest          → employee.change_employee
  helpdesk.view_ticket             → helpdesk.change_ticket
  skylinx_documents.view_documentrequest → skylinx_documents.change_documentrequest
"""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

# Directories to skip
SKIP_DIRS = {'__pycache__', '.git', 'node_modules', 'venv', 'scripts', 'scratch',
             'new logos', 'referance', 'referance code', 'referance hrms'}
SKIP_FILES = {'manage.py', '__init__.py', 'fix_all_permission_gates.py',
              'fix_permission_gates_v2.py', 'fix_permission_gates_v3.py',
              'sandeep_base_views.py', 'sandeep_base_urls.py',
              'sandeep_base_urls_fixed.py', 'sandeep_dash_urls.txt',
              'sandeep_functions.py', 'sandeep_holiday.py', 'sandeep_modified.md'}

# ── Replacement rules ────────────────────────────────────────────────────────
RULES = {
    # (old_permission, new_permission) → list of (file_glob, old_string_pattern)
    # We use literal string replacement for safety
}

# Build replacement map: for each file, list of (old_string, new_string)
replacements_by_file = {}

def add_replacement(filepath, old, new):
    """Register a replacement for a file."""
    if filepath not in replacements_by_file:
        replacements_by_file[filepath] = []
    replacements_by_file[filepath].append((old, new))

# Scan all files
print("Scanning for vulnerable gates...")
for root, dirs, files in os.walk('.'):
    # Skip unwanted dirs
    dirs[:] = [d for d in dirs if not any(
        skip in d.lower() for skip in [s.lower() for s in SKIP_DIRS])]

    for f in files:
        if not f.endswith('.py') or f in SKIP_FILES or f.startswith('fix_') or f.startswith('replace_'):
            continue
        filepath = os.path.join(root, f).replace('\\', '/')
        if any(skip in filepath.lower() for skip in ['/referance/', '/scripts/']):
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
        except Exception as e:
            continue

        # Check for each vulnerable permission
        # employee.view_employee → employee.change_employee
        if '"employee.view_employee"' in content:
            add_replacement(filepath,
                '"employee.view_employee"', '"employee.change_employee"')

        # employee.view_employeeworkinformation → employee.change_employee
        if '"employee.view_employeeworkinformation"' in content:
            add_replacement(filepath,
                '"employee.view_employeeworkinformation"', '"employee.change_employee"')

        # attendance.view_attendance → employee.change_employee
        if '"attendance.view_attendance"' in content:
            add_replacement(filepath,
                '"attendance.view_attendance"', '"employee.change_employee"')

        # leave.view_leaverequest → employee.change_employee
        if '"leave.view_leaverequest"' in content:
            add_replacement(filepath,
                '"leave.view_leaverequest"', '"employee.change_employee"')

        # helpdesk.view_ticket → helpdesk.change_ticket
        if '"helpdesk.view_ticket"' in content:
            add_replacement(filepath,
                '"helpdesk.view_ticket"', '"helpdesk.change_ticket"')

        # skylinx_documents.view_documentrequest → skylinx_documents.change_documentrequest
        if '"skylinx_documents.view_documentrequest"' in content:
            add_replacement(filepath,
                '"skylinx_documents.view_documentrequest"',
                '"skylinx_documents.change_documentrequest"')

# ── Apply replacements ────────────────────────────────────────────────────────
total_replacements = 0
total_files = 0

print(f"\nApplying replacements to {len(replacements_by_file)} files...")
for filepath, replacements in sorted(replacements_by_file.items()):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        continue

    original = content
    file_replacements = 0
    for old, new in replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            file_replacements += count

    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            total_replacements += file_replacements
            total_files += 1
            # Show first replacement detail
            old_short = replacements[0][0]
            new_short = replacements[0][1]
            print(f"  OK: {filepath} ({file_replacements} changes)")

        except Exception as e:
            print(f"  ERROR writing {filepath}: {e}")
    else:
        print(f"  --: {filepath} (no changes)")

print(f"\n{'='*60}")
print(f"Total: {total_replacements} replacements across {total_files} files")
print(f"{'='*60}")

# ── Verify remaining ──────────────────────────────────────────────────────────
print("\n=== Verifying remaining vulnerable gates ===\n")

vulnerable = [
    'employee.view_employee',
    'employee.view_employeeworkinformation',
    'attendance.view_attendance',
    'leave.view_leaverequest',
    'helpdesk.view_ticket',
    'skylinx_documents.view_documentrequest',
]

found_any = False
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not any(
        skip in d.lower() for skip in [s.lower() for s in SKIP_DIRS])]
    for f in files:
        if not f.endswith('.py') or f in SKIP_FILES or f.startswith('fix_') or f.startswith('replace_'):
            continue
        filepath = os.path.join(root, f).replace('\\', '/')
        if any(skip in filepath.lower() for skip in ['/referance/', '/scripts/']):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for perm in vulnerable:
                for match in re.finditer(re.escape(perm), content):
                    line_num = content[:match.start()].count('\n') + 1
                    if not found_any:
                        found_any = True
                    print(f"  REMAINING: {filepath}:{line_num}")
                    break
        except:
            pass

if not found_any:
    print("  ✨ ALL VULNERABLE GATES HAVE BEEN FIXED!")
else:
    print(f"\n  ⚠️  Some gates remain. Review the list above.")
