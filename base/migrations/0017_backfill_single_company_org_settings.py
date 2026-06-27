from django.db import migrations


def backfill_single_company_org_settings(apps, schema_editor):
    Company = apps.get_model("base", "Company")
    Department = apps.get_model("base", "Department")
    JobPosition = apps.get_model("base", "JobPosition")
    JobRole = apps.get_model("base", "JobRole")

    companies = list(Company.objects.all()[:2])
    if len(companies) != 1:
        return

    company = companies[0]
    for model in (Department, JobPosition, JobRole):
        for obj in model.objects.filter(company_id__isnull=True).distinct():
            obj.company_id.add(company)


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0016_alter_attachment_file_alter_baserequestfile_file_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_single_company_org_settings, migrations.RunPython.noop),
    ]
