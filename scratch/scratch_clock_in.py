import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings.base')
django.setup()
from django.test import RequestFactory
from attendance.views.clock_in_out import clock_in
from django.contrib.auth import get_user_model
from employee.models import Employee

user = get_user_model().objects.first()
req = RequestFactory().get('/attendance/clock-in/')
req.user = user
from django.contrib.sessions.middleware import SessionMiddleware
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(req)
req.session.save()
req.htmx = True
req.META['HTTP_HX_REQUEST'] = 'true'

try:
    resp = clock_in(req)
    print("Success:", resp)
except Exception as e:
    import traceback
    traceback.print_exc()
