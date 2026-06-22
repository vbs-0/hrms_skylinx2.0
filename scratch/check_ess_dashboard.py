import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("base/templates/base/ess_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Contains 'holiday':", "holiday" in html.lower())
print("Contains 'calendar':", "calendar" in html.lower())
print("Contains 'leave':", "leave" in html.lower())
