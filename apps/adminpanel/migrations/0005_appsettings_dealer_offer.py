from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0004_appsettings_ads"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="dealer_offer",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
