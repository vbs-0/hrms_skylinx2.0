import traceback
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from attendance.views.clock_in_out import clock_in

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        try:
            user = get_user_model().objects.filter(is_superuser=False).first()
            if not user:
                print("No user found")
                return
            req = RequestFactory().get('/attendance/clock-in/')
            req.user = user
            middleware = SessionMiddleware(lambda r: None)
            middleware.process_request(req)
            req.session.save()
            req.htmx = True
            req.META['HTTP_HX_REQUEST'] = 'true'
            resp = clock_in(req)
            print("Success:", resp)
        except Exception as e:
            traceback.print_exc()
