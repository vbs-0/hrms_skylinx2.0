import os
import re

root_dir = r"c:\Users\chbha\Desktop\skylinx\HRMS2.0"
pattern = re.compile(r"createElement\s*\(\s*['\"]form['\"]\)|submit\s*\(|\.submit\b", re.IGNORECASE)

results = []
for dirpath, dirnames, filenames in os.walk(root_dir):
    # Skip virtual environments and git
    if "venv" in dirpath or ".git" in dirpath or "node_modules" in dirpath:
        continue
    for filename in filenames:
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            results.append(f"{filepath}:{i}: {line.strip()}")
            except Exception as e:
                pass

with open(r"c:\Users\chbha\Desktop\skylinx\HRMS2.0\scratch\search_results.txt", "w", encoding="utf-8") as out:
    for res in results:
        out.write(res + "\n")

print(f"Done. Found {len(results)} matches.")
