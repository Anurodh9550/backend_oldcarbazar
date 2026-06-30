from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_showroom_url_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowroomGalleryItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("photo_url", models.URLField(blank=True, default="", max_length=500)),
                ("price_label", models.CharField(blank=True, default="", max_length=60)),
                ("note", models.TextField(blank=True, default="")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "showroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery",
                        to="users.dealershowroom",
                    ),
                ),
            ],
            options={
                "ordering": ("sort_order", "title"),
            },
        ),
    ]
