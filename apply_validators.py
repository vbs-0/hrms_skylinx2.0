import os
import re

import_statement = 'from skylinx.validators import SafeMimeValidator\n'

def patch_file_uploads(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add import if missing and if file contains FileField or ImageField
    if ('models.FileField' in content or 'models.ImageField' in content or 'forms.FileField' in content or 'forms.ImageField' in content) and 'SafeMimeValidator' not in content:
        # inject import after other imports
        content = import_statement + content

    # Add validators=[SafeMimeValidator()] to FileField/ImageField declarations
    # A bit naive regex, but covers most standard forms.
    # We look for models.FileField(...) or models.ImageField(...) and ensure validators= is appended.
    
    # We will do a generic replacement for models.FileField and models.ImageField
    # Only if it doesn't already have validators=
    def add_validator(match):
        inner = match.group(2)
        if 'validators=' not in inner:
            if inner.strip() == '':
                return f"{match.group(1)}(validators=[SafeMimeValidator()])"
            else:
                return f"{match.group(1)}({inner}), validators=[SafeMimeValidator()]"
        return match.group(0)
    
    new_content = re.sub(r'(models\.FileField|models\.ImageField|forms\.FileField|forms\.ImageField)\((.*?)\)', add_validator, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Patched validators in {filepath}")

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') and ('models.py' in f or 'forms.py' in f or 'forms/' in root):
            patch_file_uploads(os.path.join(root, f))
print("File upload validators applied.")
