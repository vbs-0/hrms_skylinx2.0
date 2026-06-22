import os

for root, dirs, files in os.walk("."):
    if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "nav_hour_account.html" in content:
                        print(f"File containing 'nav_hour_account.html': {filepath}")
            except Exception:
                pass
