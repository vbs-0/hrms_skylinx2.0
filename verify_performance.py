import os
import django
import time
from django.db import connection, reset_queries

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.test.client import RequestFactory
from attendance.views.views import attendance_view
from employee.views import employee_view
from project.views import project_view
from recruitment.views.views import candidate_view
from leave.views import leave_request_view, leave_type_view, leave_assign_view
from payroll.views.views import contract_view, payslip_details
from onboarding.views import onboarding_view, candidates_view
from offboarding.views import pipeline as offboarding_pipeline, request_view as offboarding_request_view

# Setup a fake request
factory = RequestFactory()

def test_view_performance(view_func, url, name):
    print(f"\n--- Testing {name} ({url}) ---")
    request = factory.get(url)
    
    # We need to simulate a logged-in user with permissions if needed.
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = None
    for u in User.objects.all():
        if getattr(u, 'employee_get', None) is not None:
            user = u
            if u.is_superuser:
                break
    if not user:
        print("No user with an employee profile found in the database.")
        return
        
    request.user = user
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore()
    session.create()
    request.session = session
    
    # Mock messages on the request
    from django.contrib.messages.storage.fallback import FallbackStorage
    request._messages = FallbackStorage(request)
    
    # In Django, standard request middleware defines request.environ.
    # Some views might access request.environ["QUERY_STRING"] or similar.
    request.environ['QUERY_STRING'] = ''
    
    from skylinx.skylinx_middlewares import _thread_locals
    _thread_locals.request = request
    
    # Run accessibility middleware simulation to populate cache
    from accessibility.middlewares import update_accessibility_cache
    cache_key = session.session_key + "accessibility_filter"
    update_accessibility_cache(cache_key, request)
    
    reset_queries()
    start_time = time.time()
    
    try:
        response = view_func(request)
        # Force rendering if it's a TemplateResponse
        if hasattr(response, 'render'):
            response.render()
        elif hasattr(response, 'content'):
            _ = response.content # access content to force evaluation
            
        end_time = time.time()
        
        queries = len(connection.queries)
        duration = end_time - start_time
        print(f"SUCCESS: View rendered without crashing.")
        print(f"Queries executed: {queries}")
        print(f"Time taken: {duration:.3f} seconds")
        
    except Exception as e:
        import traceback
        print(f"ERROR: The view crashed with error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Performance Verification...")
    print("====================================")
    
    test_view_performance(employee_view, '/employee/employee-view/', "Employee List View")
    test_view_performance(attendance_view, '/attendance/attendance-view/', "Attendance List View")
    test_view_performance(project_view, '/project/project-view/', "Project List View")
    test_view_performance(candidate_view, '/recruitment/candidate-view/', "Recruitment Candidate View")
    test_view_performance(leave_request_view, '/leave/leave-request-view/', "Leave Request View")
    test_view_performance(leave_type_view, '/leave/leave-type-view/', "Leave Type View")
    test_view_performance(leave_assign_view, '/leave/leave-assign-view/', "Leave Assign View")
    test_view_performance(contract_view, '/payroll/contract-view/', "Payroll Contract View")
    test_view_performance(payslip_details, '/payroll/payslip-details/', "Payroll Payslip View")
    test_view_performance(onboarding_view, '/onboarding/onboarding-view/', "Onboarding View")
    test_view_performance(candidates_view, '/onboarding/candidates-view/', "Onboarding Candidates View")
    test_view_performance(offboarding_pipeline, '/offboarding/pipeline/', "Offboarding Pipeline View")
    test_view_performance(offboarding_request_view, '/offboarding/request-view/', "Offboarding Request View")
    
    print("\n====================================")
    print("Verification complete.")
