import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("base/templates/base/ess_dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "holiday" in line.lower() or "calendar" in line.lower():
        print(f"{idx+1}: {line.strip()}")
