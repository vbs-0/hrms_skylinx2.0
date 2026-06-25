import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps

for app_config in apps.get_app_configs():
    print(f"App: {app_config.label}")
    for model in app_config.get_models():
        print(f"  Model: {model.__name__}")
