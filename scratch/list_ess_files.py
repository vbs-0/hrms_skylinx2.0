import os

for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root or '.gemini' in root or 'node_modules' in root:
        continue
    for file in files:
        if 'ess' in file.lower() or 'user_panel' in file.lower() or 'user-panel' in file.lower():
            print(os.path.join(root, file))
