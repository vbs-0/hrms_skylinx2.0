import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("base", "0019_worktype_geofence_exempt"),
        ("employee", "0014_sync_state_drop_legacy_salary_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuzzConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_group", models.BooleanField(default=False)),
                ("title", models.CharField(blank=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company_id", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="buzz_conversations", to="base.company")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="employee.employee")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="BuzzConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="pending", max_length=10)),
                ("message", models.CharField(blank=True, default="", max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="buzz_requests_sent", to="employee.employee")),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="buzz_requests_received", to="employee.employee")),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("requester", "target")}},
        ),
        migrations.CreateModel(
            name="BuzzMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=4000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="buzz.buzzconversation")),
                ("sender", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="buzz_messages", to="employee.employee")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="BuzzParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_read_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="buzz.buzzconversation")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="buzz_participations", to="employee.employee")),
            ],
            options={"unique_together": {("conversation", "employee")}},
        ),
    ]
