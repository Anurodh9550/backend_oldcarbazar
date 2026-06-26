# Generated manually for seller response score cache.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="seller_avg_response_hours",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="seller_response_tier",
            field=models.CharField(
                choices=[
                    ("new", "New seller"),
                    ("fast", "Fast responder"),
                    ("good", "Good responder"),
                    ("slow", "Slow responder"),
                ],
                db_index=True,
                default="new",
                max_length=10,
            ),
        ),
    ]
