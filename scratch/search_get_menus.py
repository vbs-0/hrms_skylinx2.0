import os
import re

def search_pattern(pattern, root_dir):
    matches = []
    regex = re.compile(pattern)
    for root, dirs, files in os.walk(root_dir):
        # ignore venv and git
        if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py') or file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append((filepath, line_num, line.strip()))
                except Exception:
                    pass
    return matches

results = search_pattern("get_MENUS", ".")
print(f"Found {len(results)} matches for 'get_MENUS':")
for r in results:
    print(f"- {r[0]}:{r[1]}: {r[2]}")
