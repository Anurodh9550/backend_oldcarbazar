"""Car listings + photos."""
import uuid
from django.conf import settings
from django.db import models


class Listing(models.Model):
    """A car listed for sale."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SOLD = "sold", "Sold"
        DRAFT = "draft", "Draft"

    class Moderation(models.TextChoices):
        APPROVED = "approved", "Approved"
        PENDING = "pending", "Pending"
        REJECTED = "rejected", "Rejected"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="listings",
        null=True,
        blank=True,
    )
    seller_name = models.CharField(max_length=120)
    seller_phone = models.CharField(max_length=15)
    seller_email = models.EmailField(blank=True, null=True)

    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=80, db_index=True)
    model = models.CharField(max_length=120)
    variant = models.CharField(max_length=120, blank=True, default="")
    year = models.PositiveIntegerField()

    price_label = models.CharField(max_length=40)
    price_inr = models.DecimalField(
        max_digits=12, decimal_places=2, db_index=True
    )

    kms = models.PositiveIntegerField(default=0)
    fuel = models.CharField(max_length=24)
    transmission = models.CharField(max_length=24)
    owners = models.CharField(max_length=32)
    ownership = models.CharField(max_length=32, blank=True, default="")

    body_type = models.CharField(max_length=32, blank=True, default="")
    color = models.CharField(max_length=32, blank=True, default="")
    seats = models.PositiveSmallIntegerField(default=5)
    engine_cc = models.CharField(max_length=16, blank=True, default="")
    mileage = models.CharField(max_length=24, blank=True, default="")

    registration_month = models.CharField(max_length=16, blank=True, default="")
    reg_number = models.CharField(max_length=32, blank=True, default="")
    insurance = models.CharField(max_length=64, blank=True, default="")

    location = models.CharField(max_length=80, db_index=True)
    area = models.CharField(max_length=120, blank=True, default="")

    description = models.TextField(blank=True, default="")
    features = models.JSONField(default=list, blank=True)

    cover_image = models.URLField(blank=True, default="")

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    moderation = models.CharField(
        max_length=10, choices=Moderation.choices,
        default=Moderation.PENDING, db_index=True
    )
    rejected_reason = models.TextField(blank=True, default="")

    featured = models.BooleanField(default=False, db_index=True)
    flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True, default="")

    whatsapp = models.BooleanField(default=True)
    is_seed = models.BooleanField(default=False)

    views = models.PositiveIntegerField(default=0)
    inquiries_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title


class ListingPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="photos"
    )
    url = models.URLField()
    position = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position",)

    def __str__(self) -> str:
        return f"Photo #{self.position} for {self.listing_id}"
