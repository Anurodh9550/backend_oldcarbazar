from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_dealer_showroom_availability"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dealershowroom",
            name="banner_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="dealershowroom",
            name="logo_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
