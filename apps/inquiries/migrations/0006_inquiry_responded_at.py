# Generated manually for inquiry response tracking.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inquiries", "0005_listingview"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquiry",
            name="responded_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
