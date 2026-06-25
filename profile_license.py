import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

import time
import cProfile
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
u = User.objects.filter(is_superuser=True).first()
c = Client()
c.force_login(u)

def test_load():
    return c.get('/license/')

cProfile.run('test_load()', sort='cumtime')
