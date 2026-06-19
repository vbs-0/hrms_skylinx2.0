#!/usr/bin/env python
"""Fix single-quote $(document).on('htmx:...') patterns by adding namespace dedup."""
import re

files_to_fix = [
    'leave/templates/leave/user_leave_view.html',
    'leave/templates/leave/user_leave/user_request_view.html',
    'templates/quick_access.html',
    'leave/templates/leave/leave_assign/assign_view.html',
    'leave/templates/leave/company_leave/company_leave_view.html',
    'recruitment/templates/pipeline/form/stage_update.html',
]

BASE = 'C:/Users/chbha/Desktop/skylinx/HRMS2.0'

for fp in files_to_fix:
    fullpath = BASE + '/' + fp
    with open(fullpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parts = fp.replace('\\', '/').split('/')
    fkey = parts[-2][:8] + '_' + parts[-1].replace('.html', '')[:12]
    
    # Match $(document).on('htmx:eventType' with single quotes
    pattern = r'(\$\(document\)\.on\(' + "'" + r'(htmx:[a-zA-Z]+)' + "'" + r'\s*,)'
    
    def repl(m):
        evt = m.group(2)
        return "$(document).off('" + evt + "." + fkey + "').on('" + evt + "." + fkey + "',"
    
    new_content, count = re.subn(pattern, repl, content)
    
    if count > 0:
        with open(fullpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("FIXED: " + fp + " (" + str(count) + " changes, key=" + fkey + ")")
    else:
        print("NO MATCH: " + fp)
