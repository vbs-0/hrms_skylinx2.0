from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geofencing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="geofencing",
            name="enforce",
            field=models.BooleanField(
                default=False,
                help_text="Block mobile check-in/out when outside the geofence (instead of just flagging it).",
            ),
        ),
    ]
