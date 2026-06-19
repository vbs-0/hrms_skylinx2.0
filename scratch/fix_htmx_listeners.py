#!/usr/bin/env python
"""
Batch-fix all $(document).on('htmx:...') patterns that lack namespace dedup.
Changes: $(document).on("htmx:eventType", fn) -> $(document).off("htmx:eventType.filekey").on("htmx:eventType.filekey", fn)
where filekey is derived from the template filename.
"""
import re
import os

files_to_fix = [
    "base/templates/cbv/multiple_approval_condition/form_edit.html",
    "pms/templates/cbv/meetings/meetings.html",
    "recruitment/templates/cbv/stages/title.html",
    "recruitment/templates/cbv/recruitment/rec_main.html",
    "recruitment/templates/cbv/interview/interview_home_view.html",
    "pms/templates/cbv/objectives/objective_templates.html",
    "base/templates/mail/htmx/form.html",
    "pms/templates/cbv/objectives/extended_objectives.html",
    "skylinx_views/templates/generic/skylinx_kanban_view.html",
    "payroll/templates/payroll/loan/installments.html",
    "employee/templates/cbv/disciplinary_actions/forms/create_form.html",
    "skylinx_theme/templates/cbv/allocations/employee/forms.html",
    "skylinx_theme/templates/cbv/projects/project_tab.html",
    "helpdesk/templates/helpdesk/faq/faq_view.html",
    "skylinx_theme/templates/helpdesk/faq/faq_view.html",
    "skylinx_theme/templates/cbv/exit_process/stage_order.html",
    "skylinx_theme/templates/cbv/exit_process/detail_view_tasks.html",
    "offboarding/templates/cbv/exit_process/stage_order.html",
    "offboarding/templates/cbv/exit_process/detail_view_tasks.html",
    "recruitment/templates/pipeline/nav.html",
    "base/templates/work_type_request/work_type_request_view.html",
    "templates/quick_access.html",
    "leave/templates/leave/user_leave_view.html",
    "leave/templates/leave/user_leave/user_request_view.html",
    "leave/templates/leave/company_leave/company_leave_view.html",
    "leave/templates/leave/leave_assign/assign_view.html",
    "leave/templates/leave/holiday/holiday_view.html",
    "recruitment/templates/pipeline/form/stage_update.html",
    "leave/templates/cbv/my_leave_request/form/inherit.html",
    "leave/templates/cbv/leave_requests/form/inherit.html",
]

BASE = "C:/Users/chbha/Desktop/skylinx/HRMS2.0"

def get_filekey(filepath):
    name = os.path.splitext(os.path.basename(filepath))[0]
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) >= 3:
        return parts[-3][:8] + "_" + parts[-2][:8] + "_" + name[:12]
    return name[:20]

fixed_count = 0
errors = []

for fp in files_to_fix:
    fullpath = os.path.join(BASE, fp)
    if not os.path.exists(fullpath):
        errors.append(f"NOT FOUND: {fp}")
        continue
    
    with open(fullpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filekey = get_filekey(fp)
    
    # regex: $(document).on("htmx:eventType"
    pattern = r'(\$\(document\)\.on\("(htmx:[a-zA-Z]+)"\s*,)'
    
    def make_replacement(m):
        event_type = m.group(2)
        return f'$(document).off("{event_type}.{filekey}").on("{event_type}.{filekey}",'
    
    new_content, change_count = re.subn(pattern, make_replacement, content)
    
    if change_count > 0:
        with open(fullpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"FIXED: {fp} ({change_count} changes, key={filekey})")
        fixed_count += 1
    else:
        print(f"NO MATCH: {fp}")

for e in errors:
    print(e)

print(f"\nTotal fixed: {fixed_count} files")
