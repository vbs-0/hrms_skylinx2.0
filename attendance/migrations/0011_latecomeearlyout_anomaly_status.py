from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0010_mobilelocationlog_within_geofence"),
        ("employee", "0014_sync_state_drop_legacy_salary_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancelatecomeearlyout",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("acknowledged", "Acknowledged"),
                    ("resolved", "Resolved"),
                    ("ignored", "Ignored"),
                ],
                default="open",
                max_length=15,
                verbose_name="Status",
            ),
        ),
        migrations.AddField(
            model_name="attendancelatecomeearlyout",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resolved_late_early",
                to="employee.employee",
                verbose_name="Resolved By",
            ),
        ),
        migrations.AddField(
            model_name="attendancelatecomeearlyout",
            name="resolution_note",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Resolution Note"
            ),
        ),
        migrations.AddField(
            model_name="attendancelatecomeearlyout",
            name="status_updated_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
