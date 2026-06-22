import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

client = Client()
User = get_user_model()
user = User.objects.get(username="admin")
client.force_login(user)

url_full = reverse("holiday-calendar-view")
response = client.get(url_full)
html = response.content.decode("utf-8")

print("--- STANDALONE ---")
print("Public Holidays in HTML context:", "Public Holidays" in html)
print("Approved Leaves in HTML context:", "Approved Leaves" in html)

url_dash = url_full + "?hx=1&dashboard=1"
response_dash = client.get(url_dash)
html_dash = response_dash.content.decode("utf-8")

print("--- DASHBOARD CARD ---")
print("Public Holidays in dashboard HTML context:", "Public Holidays" in html_dash)
print("Approved Leaves in dashboard HTML context:", "Approved Leaves" in html_dash)
