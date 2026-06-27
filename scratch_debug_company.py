import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()

from django.contrib.auth import get_user_model
from base.models import Company
from base.cbv.company import _company_is_user_company
from django.test import RequestFactory

User = get_user_model()
factory = RequestFactory()

users = User.objects.filter(is_superuser=True)
companies = Company.objects.all()

for user in users:
    print(f"\nUser: {user.username}, is_superuser: {user.is_superuser}")
    employee = getattr(user, "employee_get", None)
    if employee:
        work_info = getattr(employee, "employee_work_info", None)
        print(f"  Employee: {employee}, WorkInfo: {work_info}")
        if work_info:
            print(f"  Company: {work_info.company_id}")
    else:
        print("  No Employee record.")

    request = factory.get('/')
    request.user = user

    for company in companies:
        result = _company_is_user_company(request, company)
        print(f"  _company_is_user_company({company.company}): {result}")
