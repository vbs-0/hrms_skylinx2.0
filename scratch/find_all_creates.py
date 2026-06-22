import os
import re

def search_create_buttons(root_dir):
    matches = []
    # Search for files with 'Actions' and 'Create' in the same template
    for root, dirs, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'Create' in content or 'create' in content:
                            if 'Filter' in content or 'filter' in content:
                                # Look for the word "Create" inside tags
                                for match in re.finditer(r'(oh-btn|oh-btn--secondary|ion-icon)[^>]*>(.*?)Create', content, re.IGNORECASE):
                                    start = max(0, match.start() - 100)
                                    end = min(len(content), match.end() + 100)
                                    snippet = content[start:end].replace('\n', ' ')
                                    matches.append((filepath, snippet))
                except Exception:
                    pass
    return matches

results = search_create_buttons(".")
print(f"Found {len(results)} matches for 'Create' button next to buttons:")
for r in results:
    print(f"- {r[0]}: ... {r[1]} ...")
