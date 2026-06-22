import os

templates = [
    "attendance/templates/attendance/own_attendance/view_own_attendances.html",
    "attendance/templates/attendance/attendance_activity/attendance_activity_view.html",
]

for t in templates:
    print(f"=== {t} ===")
    if os.path.exists(t):
        with open(t, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for idx, line in enumerate(lines[:50], 1):
                print(f"{idx}: {line.rstrip()}")
    else:
        print("File not found")
