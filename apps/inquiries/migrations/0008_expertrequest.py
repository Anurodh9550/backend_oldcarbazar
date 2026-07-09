import uuid
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0006_appsettings_whatsapp_phone_whatsappintentlog"),
        ("inquiries", "0007_partnershipinquiry"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpertRequest",
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
                ("phone", models.CharField(db_index=True, max_length=15)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("city", models.CharField(blank=True, default="", max_length=80)),
                (
                    "requirement",
                    models.CharField(
                        choices=[
                            ("buy_car", "Buy Car"),
                            ("sell_car", "Sell Car"),
                            ("car_loan", "Car Loan"),
                            ("insurance", "Insurance"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        default="other",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("pending", "Pending"),
                            ("calling", "Calling"),
                            ("connected", "Connected"),
                            ("completed", "Completed"),
                            ("closed", "Closed"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=12,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expert_requests",
                        to="adminpanel.admin",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expert_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="expertrequest",
            index=models.Index(fields=["status", "-created_at"], name="inquiries_e_status_aa5ae5_idx"),
        ),
        migrations.AddIndex(
            model_name="expertrequest",
            index=models.Index(fields=["requirement", "-created_at"], name="inquiries_e_require_6e6f07_idx"),
        ),
    ]
