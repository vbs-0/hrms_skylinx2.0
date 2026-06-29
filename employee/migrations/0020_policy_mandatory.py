from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0019_alter_disciplinaryaction_attachment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="mandatory",
            field=models.BooleanField(
                default=False,
                help_text="Employees must accept this before accessing the HRMS.",
                verbose_name="Mandatory",
            ),
        ),
    ]
