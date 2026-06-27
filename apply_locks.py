import os
import re

file_path = 'attendance/views/requests.py'
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where Attendance.objects.get(id=attendance_id) or similar happens
    # and add .select_for_update() before .get
    content = content.replace('Attendance.objects.get', 'Attendance.objects.select_for_update().get')
    content = content.replace('Attendance.objects.filter(id__in=ids)', 'Attendance.objects.select_for_update().filter(id__in=ids)')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
print('select_for_update applied.')
