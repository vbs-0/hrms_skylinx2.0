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
            
            # The issue was that the original string ended with a comma and newline before the closing paren.
            # Example: 
            #    null=True,
            #, validators=[SafeMimeValidator()])
            fixed_content = re.sub(r',\s*, validators=\[SafeMimeValidator\(\)\]\)', r', validators=[SafeMimeValidator()])', content)
            
            # Another variant:
            #    null=True
            #, validators=[SafeMimeValidator()])
            fixed_content = re.sub(r'(\s*), validators=\[SafeMimeValidator\(\)\]\)', r', validators=[SafeMimeValidator()])', fixed_content)
            
            if content != fixed_content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                print(f"Fixed {filepath}")

print("Syntax errors patched.")
