import skylinx.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facedetection', '0003_alter_employeefacedetection_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeefacedetection',
            name='image',
            field=models.ImageField(upload_to='facedetection/', validators=[skylinx.validators.SafeMimeValidator()]),
        ),
    ]
