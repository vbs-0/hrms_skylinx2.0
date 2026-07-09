from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0018_company_ai_action_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="worktype",
            name="geofence_exempt",
            field=models.BooleanField(default=False, verbose_name="Exempt from Geo-fencing"),
        ),
    ]
