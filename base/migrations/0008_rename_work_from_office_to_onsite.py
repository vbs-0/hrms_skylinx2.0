from django.db import migrations


def rename_forward(apps, schema_editor):
    WorkType = apps.get_model("base", "WorkType")
    WorkType.objects.filter(work_type="Work From Office").update(work_type="Onsite")


def rename_back(apps, schema_editor):
    WorkType = apps.get_model("base", "WorkType")
    WorkType.objects.filter(work_type="Onsite").update(work_type="Work From Office")


class Migration(migrations.Migration):
    dependencies = [("base", "0007_companygroup")]
    operations = [migrations.RunPython(rename_forward, rename_back)]
