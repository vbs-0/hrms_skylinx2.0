from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_subscription_seat_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="yearly_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
