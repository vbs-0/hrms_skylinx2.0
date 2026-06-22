import os

templates = [
    "attendance/templates/attendance/own_attendance/view_own_attendances.html",
    "attendance/templates/attendance/own_attendance/own_empty.html",
    "attendance/templates/attendance/attendance_activity/attendance_activity_view.html",
    "attendance/templates/attendance/attendance_activity/activity_empty.html",
    "attendance/templates/attendance/work_record/work_record_view.html",
    "attendance/templates/attendance/work_record/work_record_list.html",
]

for t in templates:
    if os.path.exists(t):
        print(f"=== {t} ===")
        with open(t, 'r', encoding='utf-8') as f:
            content = f.read()
            # find all oh-btn occurrences or buttons
            for line_num, line in enumerate(content.split('\n'), 1):
                if any(x in line.lower() for x in ["oh-btn", "button", "modal-toggle", "create", "add"]):
                    print(f"Line {line_num}: {line.strip()}")
    else:
        print(f"File not found: {t}")
