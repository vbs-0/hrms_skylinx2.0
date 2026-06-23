from django.db import migrations


def to_rupee(apps, schema_editor):
    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    PayrollSettings.objects.filter(currency_symbol="$").update(
        currency_symbol="₹", position="prefix"
    )


def to_dollar(apps, schema_editor):
    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    PayrollSettings.objects.filter(currency_symbol="₹").update(currency_symbol="$")


class Migration(migrations.Migration):
    dependencies = [("payroll", "0005_form16document")]
    operations = [migrations.RunPython(to_rupee, to_dollar)]
