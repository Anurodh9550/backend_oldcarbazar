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
    # Paid boost: while `boosted_until` is in the future the listing ranks
    # just below admin-pinned featured cars in the public feed.
    boosted_until = models.DateTimeField(null=True, blank=True, db_index=True)
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

    @property
    def is_boosted(self) -> bool:
        from django.utils import timezone
        return bool(self.boosted_until and self.boosted_until > timezone.now())


class ListingBoostOrder(models.Model):
    """Server-side record of one Razorpay checkout for a listing boost.

    Mirrors the subscription `RazorpayOrder` flow but is scoped to a single
    listing + boost package. We keep a local copy so verification can prove
    which listing/package the payment was created for.
    """

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_boost_orders",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="boost_orders",
    )
    package = models.CharField(max_length=32, db_index=True)
    duration_days = models.PositiveSmallIntegerField(default=0)
    amount_inr = models.PositiveIntegerField()
    razorpay_order_id = models.CharField(max_length=120, unique=True)
    razorpay_payment_id = models.CharField(max_length=120, blank=True, default="")
    receipt = models.CharField(max_length=80, unique=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    boosted_until = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["listing", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.razorpay_order_id} · {self.listing_id} · {self.package}"


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
