import os
import re

dir_path = r'c:\Users\chbha\Desktop\skylinx\HRMS2.0'
exclude_dirs = {'.git', 'venv', 'env', '__pycache__', 'node_modules', 'migrations', 'referance code', 'referance hrms'}

replacements = [
    (re.compile(r'username="Skylinx Bot"'), 'username="Skylinx Bot"'),
    (re.compile(r"username='Skylinx Bot'"), "username='Skylinx Bot'"),
]

changed_files = 0

for root, dirs, files in os.walk(dir_path):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            new_content = content
            for pattern, repl in replacements:
                new_content = pattern.sub(repl, new_content)
                
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                changed_files += 1

print(f'Reverted {changed_files} files.')
