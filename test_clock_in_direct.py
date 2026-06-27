import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings.base')
django.setup()

import traceback
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from attendance.views.clock_in_out import clock_in
from base.models import Company, EmployeeShiftDay
from attendance.models import AttendanceGeneralSetting
from base.models import AttendanceAllowedIP
from employee.models import Employee

try:
    user = get_user_model().objects.filter(is_superuser=False).first()
    if not user:
        print("No user found")
    else:
        company = Company.objects.first()
        
        # Make sure EmployeeShiftDay exists
        for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            EmployeeShiftDay.objects.get_or_create(day=d)
            
        req = RequestFactory().get('/attendance/clock-in/')
        req.user = user
        
        # Add Session
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(req)
        req.session['selected_company'] = str(company.id)
        req.session.save()
        
        # Add messages middleware mock
        from django.contrib.messages.middleware import MessageMiddleware
        msg_middleware = MessageMiddleware(lambda r: None)
        msg_middleware.process_request(req)
        
        req.htmx = True
        req.META['HTTP_HX_REQUEST'] = 'true'
        
        print("Calling clock_in...")
        resp = clock_in(req)
        print("Success:", resp)
except Exception as e:
    traceback.print_exc()
