import os
import re

files_to_fix = [
    'facedetection/views.py',
    'whatsapp/views.py',
    'subscriptions/views.py'
]

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace @csrf_exempt with a comment
    content = re.sub(r'@csrf_exempt', r'# @csrf_exempt  # SECURITY REMEDIATION: Removed to prevent CSRF', content)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed {filepath}")

