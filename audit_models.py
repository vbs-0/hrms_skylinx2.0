import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
from base.skylinx_company_manager import SkylinxCompanyManager
from skylinx.models import SkylinxModel

bad_models = []
for m in apps.get_models():
    if issubclass(m, SkylinxModel):
        filter_path = None
        has_manager = isinstance(m.objects, SkylinxCompanyManager)
        if has_manager:
            try:
                filter_path = m.objects.get_company_filter_path()
            except Exception as e:
                pass
                
        if not filter_path:
            bad_models.append({
                'app': m._meta.app_label,
                'model': m._meta.object_name,
                'has_manager': has_manager
            })

for b in bad_models:
    print(f"{b['app']}.{b['model']} - Manager: {b['has_manager']}")
