import os
import re

def search_patterns(patterns, root_dir):
    matches = []
    regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
    for root, dirs, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py') or file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            for idx, regex in enumerate(regexes):
                                if regex.search(line):
                                    matches.append((patterns[idx], filepath, line_num, line.strip()))
                except Exception:
                    pass
    return matches

results = search_patterns(["user panel", "user_panel"], ".")
print(f"Found {len(results)} matches:")
for r in results:
    print(f"- {r[1]}:{r[2]}: {r[3]}")
