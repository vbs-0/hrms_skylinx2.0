import os
import re

directory = r'c:\Users\chbha\Desktop\skylinx\HRMS2.0'

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.html') or file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                
                # Using regex to replace the exact translated strings
                new_content = re.sub(r'\{\%\s*trans\s+[\'\"]Badge ID[\'\"]\s*\%\}', '{% trans "Employee ID" %}', new_content, flags=re.IGNORECASE)
                new_content = re.sub(r'\{\%\s*trans\s+[\'\"]Badge Id[\'\"]\s*\%\}', '{% trans "Employee ID" %}', new_content, flags=re.IGNORECASE)
                new_content = re.sub(r'\{\%\s*trans\s+[\'\"]Badge id[\'\"]\s*\%\}', '{% trans "Employee ID" %}', new_content, flags=re.IGNORECASE)
                
                # other strings
                new_content = new_content.replace('\"Employee ID\"', '\"Employee ID\"')
                new_content = new_content.replace('\'Employee ID\'', '\'Employee ID\'')
                new_content = new_content.replace('Employee ID', 'Employee ID')
                new_content = new_content.replace('\"Employee ID Error\"', '\"Employee ID Error\"')
                new_content = new_content.replace('\"Employee Employee ID\"', '\"Employee ID\"')
                new_content = new_content.replace('\"Manager Employee ID\"', '\"Manager Employee ID\"')
                new_content = new_content.replace('\"Member Employee ID\"', '\"Member Employee ID\"')
                
                new_content = new_content.replace('>Employee ID<', '>Employee ID<')
                new_content = new_content.replace('>Employee ID<', '>Employee ID<')
                new_content = new_content.replace('>Employee ID<', '>Employee ID<')
                
                # Careful with 'Employee ID' not to break variable names like badge_id
                # So we replace the capitalized words in normal text
                new_content = new_content.replace(' Employee ID', ' Employee ID')
                new_content = new_content.replace(' Employee ID', ' Employee ID')
                new_content = new_content.replace(' Employee ID', ' Employee ID')
                new_content = new_content.replace('\"Employee ID', '\"Employee ID')
                new_content = new_content.replace('\'Employee ID', '\'Employee ID')
                new_content = new_content.replace('\"Employee ID', '\"Employee ID')
                new_content = new_content.replace('\'Employee ID', '\'Employee ID')
                new_content = new_content.replace('\"Employee ID', '\"Employee ID')
                new_content = new_content.replace('\'Employee ID', '\'Employee ID')
                new_content = new_content.replace('Employee ID:', 'Employee ID:')
                new_content = new_content.replace('Employee ID:', 'Employee ID:')
                new_content = new_content.replace('Employee ID:', 'Employee ID:')
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f'Updated {filepath}')
            except Exception as e:
                pass
