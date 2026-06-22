import os

def find_dollars():
    for root, dirs, files in os.walk('c:/Users/chbha/Desktop/skylinx/HRMS2.0/payroll/templates'):
        for file in files:
            if not file.endswith('.html'): continue
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '$' in line and not line.strip().startswith('$(') and not '$.' in line and not '$(\'' in line and not '$(\"' in line:
                    # check if $ is inside {% ... %} or {{ ... }} but not part of jquery
                    # Actually just print them all except obvious jquery
                    if '$(' in line:
                        pass
                    else:
                        print(f'{path}:{i+1}: {line.strip()}')

find_dollars()
