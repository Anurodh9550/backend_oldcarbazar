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
