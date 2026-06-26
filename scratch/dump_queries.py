import os
import sys
import django
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.test.client import RequestFactory
from django.db import connection, reset_queries
from employee.views import employee_view
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from skylinx.skylinx_middlewares import _thread_locals

factory = RequestFactory()
request = factory.get('/employee/employee-view/')

User = get_user_model()
user = None
for u in User.objects.all():
    if getattr(u, 'employee_get', None) is not None:
        user = u
        if u.is_superuser:
            break

request.user = user
session = SessionStore()
session.create()
request.session = session
request.environ['QUERY_STRING'] = ''
_thread_locals.request = request

from accessibility.middlewares import update_accessibility_cache
cache_key = session.session_key + "accessibility_filter"
update_accessibility_cache(cache_key, request)

# Hook into DB connection queries
from django.db.backends.signals import connection_created
from django.dispatch import receiver

query_traces = []

@receiver(connection_created)
def connection_hook(sender, connection, **kwargs):
    # We can't easily hook into individual executions without a custom cursor wrapper,
    # but Django connection.queries already records SQL.
    pass

# We will patch django's cursor execute instead
from django.db.backends.utils import CursorWrapper

original_execute = CursorWrapper.execute
def hook_execute(self, sql, params=None):
    tb = "".join(traceback.format_stack())
    query_traces.append((sql, tb))
    return original_execute(self, sql, params)
CursorWrapper.execute = hook_execute

response = employee_view(request)
if hasattr(response, 'render'):
    response.render()
elif hasattr(response, 'content'):
    _ = response.content

print(f"Total queries intercepted: {len(query_traces)}")

# Group traces by SQL/pattern
from collections import Counter
frequencies = Counter(sql for sql, tb in query_traces)

print("\n--- Top 5 most frequent queries with stack traces ---")
for sql, count in frequencies.most_common(5):
    print("=" * 80)
    print(f"FREQUENCY: {count} times")
    print(f"SQL: {sql}")
    # Print one traceback for this SQL
    for s, tb in query_traces:
        if s == sql:
            print("Traceback:")
            # Split and print all lines to avoid truncation
            for line in tb.split("\n"):
                print("  ", line)
            break
