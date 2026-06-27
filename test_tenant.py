import os
import django
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from subscriptions.views import create_tenant

def run():
    try:
        create_tenant("TestCompany123", "testadmin123", "test@test.com", "pass", None)
        print("Success!")
    except Exception as e:
        print("Error:")
        traceback.print_exc()

if __name__ == "__main__":
    run()
