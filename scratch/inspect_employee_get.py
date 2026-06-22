import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username="admin")

# Let's inspect user.employee_get and how it works
print("Type of user.employee_get:", type(user.employee_get) if hasattr(user, 'employee_get') else "No employee_get attribute")
if hasattr(user, 'employee_get'):
    print("Value:", user.employee_get)
