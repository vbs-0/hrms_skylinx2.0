import os
import re

with open("attendance/urls.py", "r", encoding="utf-8") as f:
    urls_content = f.read()

print("URL patterns matching work-records, attendance-activity, view-my-attendance:")
for line in urls_content.split('\n'):
    if any(k in line for k in ["work-records", "attendance-activity", "view-my-attendance"]):
        print("-", line.strip())
