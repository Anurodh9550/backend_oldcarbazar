import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def set_default_whatsapp_numbers(apps, schema_editor):
    AppSettings = apps.get_model("adminpanel", "AppSettings")
    AppSettings.objects.filter(id=1).update(
        support_phone="+91 91358 95389",
        whatsapp_phone="919135895389",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0005_appsettings_dealer_offer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="whatsapp_phone",
            field=models.CharField(default="919135895389", max_length=32),
        ),
        migrations.AlterField(
            model_name="appsettings",
            name="support_phone",
            field=models.CharField(default="+91 91358 95389", max_length=32),
        ),
        migrations.CreateModel(
            name="WhatsAppIntentLog",
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
                    "intent",
                    models.CharField(
                        choices=[
                            ("sell", "Sell via concierge"),
                            ("buy", "Buy via concierge"),
                            ("loan", "Loan help"),
                            ("help", "Support"),
                            ("seller_contact", "Contact listing seller"),
                            ("share_listing", "Share listing"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("listing_id", models.CharField(blank=True, default="", max_length=64)),
                ("city", models.CharField(blank=True, default="", max_length=80)),
                ("language", models.CharField(blank=True, default="en", max_length=8)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="whatsapp_intents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.RunPython(set_default_whatsapp_numbers, migrations.RunPython.noop),
    ]
