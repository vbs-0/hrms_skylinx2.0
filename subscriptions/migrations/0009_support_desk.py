import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0008_alter_aisettings_max_action_level"),
        ("base", "0019_worktype_geofence_exempt"),
        ("employee", "0014_sync_state_drop_legacy_salary_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("forward_email", models.EmailField(blank=True, default="", max_length=254, verbose_name="Support notification email")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Support Settings"},
        ),
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=150)),
                ("message", models.TextField(max_length=3000)),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved")], default="open", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_tickets", to="base.company")),
                ("raised_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="employee.employee")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
