import os
import re

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
            except Exception:
                continue
            
            # Fix error where validators got placed inside _("...") 
            # Example: _("Document"), validators=[SafeMimeValidator()]
            # Should be: _("Document"), validators=[SafeMimeValidator()]
            
            # Regex to find _("something"), validators=[SafeMimeValidator()]
            # and replace it with _("something"), validators=[SafeMimeValidator()]
            
            fixed_content = re.sub(
                r'_\(([\'"].*?[\'"]),\s*validators=\[SafeMimeValidator\(\)\]\)',
                r'_(\1), validators=[SafeMimeValidator()]',
                content
            )
            
            if content != fixed_content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                print(f"Fixed {filepath}")

print("Translation function syntax errors patched.")
