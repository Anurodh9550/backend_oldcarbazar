from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0003_appsettings_loan_tools_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="ads",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
