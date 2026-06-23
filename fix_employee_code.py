import os
def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('"Employee Code"', '"Employee ID"')
    content = content.replace("'Employee Code'", "'Employee ID'")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('c:/Users/chbha/Desktop/skylinx/HRMS2.0/employee/methods/methods.py')
replace_in_file('c:/Users/chbha/Desktop/skylinx/HRMS2.0/employee/models.py')
replace_in_file('c:/Users/chbha/Desktop/skylinx/HRMS2.0/employee/forms.py')
print('Done')
