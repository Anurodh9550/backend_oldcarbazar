"""Virtual Showroom + Car Availability for dealers (sellers)."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DealerShowroom(models.Model):
    """One mini-website profile per dealer/seller."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dealer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="showroom",
    )
    enabled = models.BooleanField(default=True)
    banner_url = models.URLField(max_length=500, blank=True, default="")
    logo_url = models.URLField(max_length=500, blank=True, default="")
    tagline = models.CharField(max_length=200, blank=True, default="")
    about = models.TextField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    whatsapp = models.CharField(max_length=15, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"Showroom: {self.dealer.name}"


class ShowroomTeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    showroom = models.ForeignKey(
        DealerShowroom,
        on_delete=models.CASCADE,
        related_name="team",
    )
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True, default="")
    photo_url = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class ShowroomReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    showroom = models.ForeignKey(
        DealerShowroom,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    author = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(default=5)
    text = models.TextField()
    review_date = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.author} ({self.rating}★)"


class ListingAvailability(models.Model):
    """Per-listing stock status shown on Virtual Showroom."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        COMING_SOON = "coming_soon", "Coming Soon"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="availability",
    )
    dealer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_availabilities",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    note = models.TextField(blank=True, default="")
    available_from = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["dealer", "status"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.listing_id} → {self.status}"
