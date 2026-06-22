import os

empty_files = [
    "attendance/templates/attendance/attendance/validate_attendance_empty.html",
    "attendance/templates/attendance/attendance_account/overtime_empty.html",
    "attendance/templates/attendance/attendance_activity/activity_empty.html",
    "attendance/templates/attendance/late_come_early_out/reports_empty.html",
    "attendance/templates/attendance/own_attendance/own_empty.html",
]

for f_path in empty_files:
    print(f"=== {f_path} ===")
    if os.path.exists(f_path):
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for line_num, line in enumerate(content.split('\n'), 1):
                if any(x in line.lower() for x in ["oh-btn", "button", "modal-toggle", "create", "add"]):
                    print(f"Line {line_num}: {line.strip()}")
    else:
        print("File not found")
