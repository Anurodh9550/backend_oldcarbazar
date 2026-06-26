# Generated manually for trust & video fields on listings.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0004_listingboostorder_base_inr_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="video_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listing",
            name="truth_declaration",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="listing",
            name="truth_declared_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
