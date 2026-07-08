from django.db import migrations, models


def copy_company_id_to_companies(apps, schema_editor):
    DynamicEmailConfiguration = apps.get_model("base", "DynamicEmailConfiguration")
    for cfg in DynamicEmailConfiguration.objects.exclude(company_id__isnull=True):
        cfg.companies.add(cfg.company_id_id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0018_company_ai_action_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="dynamicemailconfiguration",
            name="companies",
            field=models.ManyToManyField(blank=True, to="base.company", verbose_name="Companies"),
        ),
        migrations.RunPython(copy_company_id_to_companies, noop_reverse),
        migrations.RemoveField(
            model_name="dynamicemailconfiguration",
            name="company_id",
        ),
    ]
