import os

for root, dirs, files in os.walk("attendance/templates"):
    for file in files:
        if "nav" in file.lower():
            print(os.path.join(root, file))
