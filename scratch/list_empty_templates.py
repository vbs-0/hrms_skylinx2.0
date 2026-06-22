import os

for root, dirs, files in os.walk("attendance/templates"):
    for file in files:
        if "empty" in file.lower():
            print(os.path.join(root, file))
