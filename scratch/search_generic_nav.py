import os

for root, dirs, files in os.walk("attendance/templates"):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "skylinx_nav.html" in content:
                        print(f"Template including skylinx_nav.html: {filepath}")
            except Exception:
                pass
