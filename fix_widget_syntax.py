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
            
            # Fix error where validators got placed inside widget=forms.TextInput(...)
            # Example: widget=forms.TextInput(attrs={'class': '...'}), validators=[SafeMimeValidator()]
            # Should be: widget=forms.TextInput(attrs={'class': '...'}), validators=[SafeMimeValidator()]
            
            fixed_content = re.sub(
                r'\}, validators=\[SafeMimeValidator\(\)\]\)',
                r'}), validators=[SafeMimeValidator()]',
                content
            )
            # also handle cases without attrs dict but just widget=...
            fixed_content = re.sub(
                r'widget=forms\.(.*?)\((.*?),\s*validators=\[SafeMimeValidator\(\)\]\)',
                r'widget=forms.\1(\2), validators=[SafeMimeValidator()]',
                fixed_content, flags=re.DOTALL
            )
            
            if content != fixed_content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                print(f"Fixed {filepath}")

print("Widget syntax errors patched.")
