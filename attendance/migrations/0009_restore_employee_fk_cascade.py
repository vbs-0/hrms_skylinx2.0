from django.db import migrations, models
import django.db.models.deletion


def delete_orphan_rows(apps, schema_editor):
    """
    Rows created while employee_id was on_delete=SET_NULL may have a NULL
    employee_id. Those orphans both crash any employee_id dereference and would
    block the NOT NULL alteration below, so drop them before re-tightening the FK.
    """
    for model_name in (
        "AttendanceActivity",
        "AttendanceRequestComment",
        "AttendanceOverTime",
        "WorkRecords",
    ):
        model = apps.get_model("attendance", model_name)
        model.objects.filter(employee_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0008_alter_attendancerequestfile_file_and_more"),
        ("employee", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_orphan_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="attendanceactivity",
            name="employee_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_attendance_activities",
                to="employee.employee",
                verbose_name="Employee",
            ),
        ),
        migrations.AlterField(
            model_name="attendance",
            name="employee_id",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_attendances",
                to="employee.employee",
                verbose_name="Employee",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerequestcomment",
            name="employee_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="employee.employee",
            ),
        ),
        migrations.AlterField(
            model_name="attendanceovertime",
            name="employee_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_overtime",
                to="employee.employee",
                verbose_name="Employee",
            ),
        ),
        migrations.AlterField(
            model_name="workrecords",
            name="employee_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="employee.employee",
                verbose_name="Employee",
            ),
        ),
    ]
