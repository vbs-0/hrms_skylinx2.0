import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/holiday_calendar_output.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "Public Holidays" in line or "Approved Leaves" in line:
        print(f"--- Match at line {idx+1} ---")
        for i in range(max(0, idx - 5), min(len(lines), idx + 20)):
            print(f"{i+1}: {lines[i].rstrip()}")
