from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="loan_tools_content",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
