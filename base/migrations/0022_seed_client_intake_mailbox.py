from django.db import migrations


def seed_intake(apps, schema_editor):
    D = apps.get_model("base", "DynamicEmailConfiguration")
    if D.objects.filter(purpose="client_intake").exists():
        return
    D.objects.create(
        purpose="client_intake",
        host="mail.emplinx.com",
        port=465,
        username="support@emplinx.com",
        password="Emplinx2026",
        from_email="support@emplinx.com",
        display_name="Emplinx Onboarding",
        use_tls=False,
        use_ssl=True,
        fail_silently=False,
        use_dynamic_display_name=False,
        is_primary=False,
        timeout=30,
    )


def unseed_intake(apps, schema_editor):
    D = apps.get_model("base", "DynamicEmailConfiguration")
    D.objects.filter(purpose="client_intake").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0021_dynamicemailconfiguration_purpose"),
    ]

    operations = [
        migrations.RunPython(seed_intake, unseed_intake),
    ]
