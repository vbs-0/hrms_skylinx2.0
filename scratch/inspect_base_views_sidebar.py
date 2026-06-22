import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("base/views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for idx in range(1115, min(len(lines), 1145)):
    print(f"{idx+1}: {lines[idx].rstrip()}")
