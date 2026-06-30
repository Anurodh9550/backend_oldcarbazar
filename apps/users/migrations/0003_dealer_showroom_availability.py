# Generated manually for Virtual Showroom + Car Availability

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0005_listing_trust_fields"),
        ("users", "0002_seller_response_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DealerShowroom",
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
                ("enabled", models.BooleanField(default=True)),
                ("banner_url", models.URLField(blank=True, default="")),
                ("logo_url", models.URLField(blank=True, default="")),
                ("tagline", models.CharField(blank=True, default="", max_length=200)),
                ("about", models.TextField(blank=True, default="")),
                ("address", models.TextField(blank=True, default="")),
                ("whatsapp", models.CharField(blank=True, default="", max_length=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="showroom",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-updated_at",),
            },
        ),
        migrations.CreateModel(
            name="ShowroomTeamMember",
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
                ("name", models.CharField(max_length=120)),
                ("role", models.CharField(blank=True, default="", max_length=120)),
                ("photo_url", models.URLField(blank=True, default="")),
                ("bio", models.TextField(blank=True, default="")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "showroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team",
                        to="users.dealershowroom",
                    ),
                ),
            ],
            options={
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="ShowroomReview",
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
                ("author", models.CharField(max_length=120)),
                ("rating", models.PositiveSmallIntegerField(default=5)),
                ("text", models.TextField()),
                ("review_date", models.CharField(blank=True, default="", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "showroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="users.dealershowroom",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="ListingAvailability",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("available", "Available"),
                            ("reserved", "Reserved"),
                            ("sold", "Sold"),
                            ("coming_soon", "Coming Soon"),
                        ],
                        db_index=True,
                        default="available",
                        max_length=16,
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("available_from", models.DateField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="listing_availabilities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "listing",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="availability",
                        to="listings.listing",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="listingavailability",
            index=models.Index(
                fields=["dealer", "status"], name="users_listi_dealer__a8f3c2_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="listingavailability",
            index=models.Index(
                fields=["updated_at"], name="users_listi_updated_91b4e1_idx"
            ),
        ),
    ]
