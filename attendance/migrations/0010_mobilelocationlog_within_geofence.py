from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0009_restore_employee_fk_cascade"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobilelocationlog",
            name="within_geofence",
            field=models.BooleanField(default=True),
        ),
    ]
