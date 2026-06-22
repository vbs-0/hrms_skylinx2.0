import os
import re

with open("base/views.py", "r", encoding="utf-8") as f:
    content = f.read()

matches = re.findall(r"request\.user\.[a-zA-Z0-9_]+", content)
print("Unique user patterns in base/views.py:")
for m in set(matches):
    print(f"- {m}")
