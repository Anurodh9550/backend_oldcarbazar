import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inquiries", "0006_inquiry_responded_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnershipInquiry",
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
                ("business_name", models.CharField(max_length=160)),
                ("contact_person", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(db_index=True, max_length=15)),
                (
                    "partnership_type",
                    models.CharField(
                        choices=[
                            ("dealer", "Dealer / Showroom"),
                            ("insurance", "Insurance"),
                            ("service", "Service / Inspection"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("message", models.TextField()),
                ("city", models.CharField(blank=True, default="", max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Partnership inquiry",
                "verbose_name_plural": "Partnership inquiries",
                "ordering": ("-created_at",),
            },
        ),
    ]
