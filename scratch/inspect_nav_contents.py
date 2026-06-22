import os

nav_files = [
    "attendance/templates/attendance/attendance_account/nav.html",
    "attendance/templates/attendance/attendance_activity/nav.html",
    "attendance/templates/attendance/late_come_early_out/nav.html",
    "attendance/templates/attendance/own_attendance/nav.html",
    "attendance/templates/cbv/hour_account/nav_hour_account.html",
]

for f_path in nav_files:
    print(f"=== {f_path} ===")
    if os.path.exists(f_path):
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # print lines containing oh-btn, toggle, modal, create, add
            for line_num, line in enumerate(content.split('\n'), 1):
                if any(x in line.lower() for x in ["oh-btn", "button", "modal-toggle", "create", "add"]):
                    print(f"Line {line_num}: {line.strip()}")
    else:
        print("File not found")
