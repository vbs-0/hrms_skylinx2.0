import os
import re

def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find legal_editor and replace its decorators
    if "def legal_editor" in content:
        # replace @csrf_exempt with @login_required (and maybe permission check)
        content = re.sub(r'@csrf_exempt\s+def legal_editor', r'@login_required\ndef legal_editor', content)
        if "from django.contrib.auth.decorators import login_required" not in content:
            content = "from django.contrib.auth.decorators import login_required\n" + content
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed {filepath}")

process_file('base/views.py')
