from django.db import migrations

def rename_skylinx_companies(apps, schema_editor):
    Company = apps.get_model('base', 'Company')
    for company in Company.objects.all():
        if company.company and 'skylinx' in company.company.lower():
            company.company = 'EMPLINX'
            company.save()

class Migration(migrations.Migration):

    dependencies = [
        ('base', '0011_legaldocument'),
    ]

    operations = [
        migrations.RunPython(rename_skylinx_companies),
    ]
