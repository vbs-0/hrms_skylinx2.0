import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from base.models import Company, WorkType

company = Company.objects.get(id=1)
wt, created = WorkType.objects.get_or_create(work_type="Office")
if created:
    wt.company_id.set([company])
print(f"WorkType created: {created}, companies: {[c.company for c in wt.company_id.all()]}")
