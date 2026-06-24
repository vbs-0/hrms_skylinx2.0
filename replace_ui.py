import os, re
path = r'c:\Users\chbha\Desktop\skylinx\HRMS2.0'
count = 0

pattern_trans = re.compile(r'({%\s*trans\s+[\'\"])(.*?)([\'\"]\s*%})')
pattern_title = re.compile(r'(title=[\'\"])(.*?)([\'\"])')
pattern_alt = re.compile(r'(alt=[\'\"])(.*?)([\'\"])')
pattern_text = re.compile(r'(>)([^<]*)(<)')

def replace_text(text):
    text = re.sub(r'(?i)Reimbursements?', 'Expenses', text)
    text = re.sub(r'(?i)Encashments?', 'Expenses', text)
    return text

def replacer_trans(match):
    return match.group(1) + replace_text(match.group(2)) + match.group(3)

def replacer_attr(match):
    return match.group(1) + replace_text(match.group(2)) + match.group(3)

def replacer_text(match):
    return match.group(1) + replace_text(match.group(2)) + match.group(3)

for root, dirs, files in os.walk(path):
    if '.git' in root or 'venv' in root or 'env' in root:
        continue
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = pattern_trans.sub(replacer_trans, content)
            new_content = pattern_text.sub(replacer_text, new_content)
            new_content = pattern_title.sub(replacer_attr, new_content)
            new_content = pattern_alt.sub(replacer_attr, new_content)

            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
                print(f'Updated {filepath}')

print(f'Total files updated: {count}')
