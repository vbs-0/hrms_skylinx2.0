import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings.base")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from base.models import Company, Announcement
from employee.models import Employee
from base.views import edit_home_logo_card, edit_home_announcement
from employee.sidebar import shift_roster_accessibility

def test_permissions():
    User = get_user_model()
    factory = RequestFactory()
    
    # 1. Resolve superuser (root admin) who has an active employee
    superuser_emp = Employee.objects.filter(is_active=True, employee_user_id__is_superuser=True).first()
    if superuser_emp:
        superuser = superuser_emp.employee_user_id
    else:
        superuser = User.objects.filter(is_superuser=True, is_active=True).first()
        if not superuser:
            print("No active superuser found in database!")
            return
            
    # 2. Resolve admin user with employee
    admin_emp = Employee.objects.filter(is_active=True, employee_user_id__is_superuser=False).first()
    if not admin_emp:
        print("No active employee found in database!")
        return
    normal_admin = admin_emp.employee_user_id
    
    # Grant permissions temporarily to this admin
    company_ct = ContentType.objects.get_for_model(Company)
    ann_ct = ContentType.objects.get_for_model(Announcement)
    change_company = Permission.objects.get(codename="change_company", content_type=company_ct)
    change_announcement = Permission.objects.get(codename="change_announcement", content_type=ann_ct)
    
    normal_admin.user_permissions.add(change_company, change_announcement)
    
    # 3. Resolve regular user with employee
    regular_emp = Employee.objects.filter(is_active=True, employee_user_id__is_superuser=False).exclude(employee_user_id=normal_admin).first()
    if not regular_emp:
        print("No second active employee found in database to act as regular user!")
        return
    regular_user = regular_emp.employee_user_id
    
    # Make sure regular user does NOT have the change_company/change_announcement permissions
    regular_user.user_permissions.remove(change_company, change_announcement)
    
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.messages.storage.fallback import FallbackStorage
    
    # --- Test Logo Card Permissions ---
    # A. Superuser
    req_logo_super = factory.post("/edit-home-logo-card/")
    req_logo_super.user = superuser
    req_logo_super.session = SessionStore()
    req_logo_super._messages = FallbackStorage(req_logo_super)
    
    # B. Company admin
    req_logo_admin = factory.post("/edit-home-logo-card/")
    req_logo_admin.user = normal_admin
    req_logo_admin.session = SessionStore()
    req_logo_admin._messages = FallbackStorage(req_logo_admin)
    
    # C. Regular user
    req_logo_regular = factory.post("/edit-home-logo-card/")
    req_logo_regular.user = regular_user
    req_logo_regular.session = SessionStore()
    req_logo_regular._messages = FallbackStorage(req_logo_regular)
    
    res_logo_super = edit_home_logo_card(req_logo_super)
    res_logo_admin = edit_home_logo_card(req_logo_admin)
    res_logo_regular = edit_home_logo_card(req_logo_regular)
    
    print(f"Superuser edit_home_logo_card status: {res_logo_super.status_code} (Expected: 200 OK or 302 Redirect)")
    print(f"Company Admin edit_home_logo_card status: {res_logo_admin.status_code} (Expected: 200 OK or 302 Redirect)")
    print(f"Regular User edit_home_logo_card status: {res_logo_regular.status_code} (Expected: 403 Forbidden)")
    
    # --- Test Announcement Permissions ---
    # A. Superuser
    req_ann_super = factory.post("/edit-home-announcement/")
    req_ann_super.user = superuser
    req_ann_super.session = SessionStore()
    req_ann_super._messages = FallbackStorage(req_ann_super)
    
    # B. Company admin
    req_ann_admin = factory.post("/edit-home-announcement/")
    req_ann_admin.user = normal_admin
    req_ann_admin.session = SessionStore()
    req_ann_admin._messages = FallbackStorage(req_ann_admin)
    
    # C. Regular user
    req_ann_regular = factory.post("/edit-home-announcement/")
    req_ann_regular.user = regular_user
    req_ann_regular.session = SessionStore()
    req_ann_regular._messages = FallbackStorage(req_ann_regular)
    
    res_ann_super = edit_home_announcement(req_ann_super)
    res_ann_admin = edit_home_announcement(req_ann_admin)
    res_ann_regular = edit_home_announcement(req_ann_regular)
    
    print(f"Superuser edit_home_announcement status: {res_ann_super.status_code} (Expected: 200 OK or 302 Redirect)")
    print(f"Company Admin edit_home_announcement status: {res_ann_admin.status_code} (Expected: 200 OK or 302 Redirect)")
    print(f"Regular User edit_home_announcement status: {res_ann_regular.status_code} (Expected: 403 Forbidden)")
    
    # Test Shift Roster Sidebar visibility
    is_roster_visible = shift_roster_accessibility(req_logo_admin, None, None)
    print(f"Shift Roster menu visibility for admin user: {is_roster_visible} (Expected: False)")

if __name__ == "__main__":
    test_permissions()
