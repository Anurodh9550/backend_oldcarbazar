"""Buyer ↔ seller inquiries / messages."""
import uuid
from django.conf import settings
from django.db import models


class Inquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        RESPONDED = "responded", "Responded"
        CLOSED = "closed", "Closed"
        SPAM = "spam", "Spam"

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        CALL = "call", "Call"
        FORM = "form", "Form"
        CHAT = "chat", "Chat"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="inquiries"
    )
    listing_title = models.CharField(max_length=200)
    listing_price = models.CharField(max_length=40, blank=True, default="")

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="inquiries_made", null=True, blank=True,
    )
    buyer_name = models.CharField(max_length=120)
    buyer_phone = models.CharField(max_length=15)
    buyer_email = models.EmailField(blank=True, null=True)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="inquiries_received", null=True, blank=True,
    )
    seller_name = models.CharField(max_length=120)

    message = models.TextField()
    channel = models.CharField(
        max_length=10, choices=Channel.choices, default=Channel.FORM
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    city = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Inquiries"

    def __str__(self) -> str:
        return f"{self.buyer_name} → {self.listing_title}"


class TestDriveBooking(models.Model):
    """A buyer-requested test drive for a listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="test_drives",
    )
    listing_title = models.CharField(max_length=200)

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="test_drives",
        null=True,
        blank=True,
    )
    buyer_name = models.CharField(max_length=120)
    buyer_phone = models.CharField(max_length=15)
    buyer_email = models.EmailField(blank=True, null=True)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="received_test_drives",
        null=True,
        blank=True,
    )

    scheduled_at = models.DateTimeField()
    location_note = models.CharField(max_length=255, blank=True, default="")
    message = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    seller_response = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Test drive booking"
        verbose_name_plural = "Test drive bookings"

    def __str__(self) -> str:
        return f"{self.buyer_name} → {self.listing_title} ({self.scheduled_at:%d %b})"


class Offer(models.Model):
    """A price offer from a buyer to a seller for a specific listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        COUNTERED = "countered", "Countered"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    listing_title = models.CharField(max_length=200)
    listing_price_inr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="offers_made",
        null=True,
        blank=True,
    )
    buyer_name = models.CharField(max_length=120)
    buyer_phone = models.CharField(max_length=15)
    buyer_email = models.EmailField(blank=True, null=True)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="offers_received",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    counter_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    message = models.TextField(blank=True, default="")
    seller_response = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.buyer_name} → {self.listing_title} (₹{self.amount})"
