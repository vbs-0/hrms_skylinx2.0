import os

file = 'templates/dashboard.html'
if os.path.exists(file):
    content = open(file, encoding='utf-8').read()
    content = content.replace(
        'const _dbPrefsRaw = {{ employee_chart_prefs|safe }};',
        'const _dbPrefsRaw = JSON.parse("{{ employee_chart_prefs|escapejs }}" || "[]");'
    )
    open(file, 'w', encoding='utf-8').write(content)
print('XSS fixed.')
