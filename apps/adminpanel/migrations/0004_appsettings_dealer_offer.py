# Generated manually for dealer_offer JSON field on AppSettings.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0003_appsettings_ads"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="dealer_offer",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
