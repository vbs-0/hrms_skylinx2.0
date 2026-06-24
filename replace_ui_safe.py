import os, re
path = r'c:\Users\chbha\Desktop\skylinx\HRMS2.0'
count = 0

def replacer_trans(match):
    text = match.group(2)
    original_text = text
    text = re.sub(r'(?i)\breimbursements\b', 'Expenses', text)
    text = re.sub(r'(?i)\breimbursement\b', 'Expenses', text)
    text = re.sub(r'(?i)\bencashments\b', 'Expenses', text)
    text = re.sub(r'(?i)\bencashment\b', 'Expenses', text)
    if text != original_text:
        return match.group(1) + text + match.group(3)
    return match.group(0)

pattern_trans = re.compile(r'({%\s*trans\s+[\'\"])(.*?)([\'\"]\s*%})')
# also handle title="..." and alt="..."
pattern_title = re.compile(r'(title=[\'\"])(.*?)([\'\"])')
pattern_alt = re.compile(r'(alt=[\'\"])(.*?)([\'\"])')
pattern_placeholder = re.compile(r'(placeholder=[\'\"])(.*?)([\'\"])')
pattern_aria = re.compile(r'(aria-label=[\'\"])(.*?)([\'\"])')

for root, dirs, files in os.walk(path):
    if '.git' in root or 'venv' in root or 'env' in root:
        continue
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = pattern_trans.sub(replacer_trans, content)
            new_content = pattern_title.sub(replacer_trans, new_content)
            new_content = pattern_alt.sub(replacer_trans, new_content)
            new_content = pattern_placeholder.sub(replacer_trans, new_content)
            new_content = pattern_aria.sub(replacer_trans, new_content)

            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
                print(f'Updated {filepath}')

print(f'Total files updated: {count}')
