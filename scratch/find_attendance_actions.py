import os
import re

def search_patterns(patterns, root_dir):
    matches = []
    regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
    for root, dirs, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Search for buttons, links or elements with 'create' or 'add' or toggles
                        for idx, regex in enumerate(regexes):
                            for match in regex.finditer(content):
                                # print the context (surrounding 60 chars)
                                start = max(0, match.start() - 30)
                                end = min(len(content), match.end() + 50)
                                snippet = content[start:end].replace('\n', ' ')
                                matches.append((filepath, patterns[idx], snippet))
                except Exception:
                    pass
    return matches

patterns = [
    r'oh-btn',
    r'modal-toggle',
    r'data-target="#add',
    r'data-target="#create',
    r'create',
    r'add'
]
results = search_patterns(patterns, "attendance/templates")
print(f"Found {len(results)} matches in attendance templates:")
# Filter results to look for actual HTML tags that are buttons/links/actions with Create/Add
action_matches = []
for filepath, pattern, snippet in results:
    if '<button' in snippet or '<a ' in snippet or 'oh-btn' in snippet:
        # Ignore common non-create patterns
        if 'filter' in snippet.lower() or 'search' in snippet.lower() or 'export' in snippet.lower() or 'import' in snippet.lower():
            continue
        action_matches.append((filepath, snippet))

# Print unique matches per file
printed = set()
for filepath, snippet in action_matches:
    key = (filepath, snippet[:50])
    if key not in printed:
        print(f"- {filepath}: ... {snippet} ...")
        printed.add(key)
