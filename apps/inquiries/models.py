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


class ListingView(models.Model):
    """A view-lead: a logged-in customer opened a seller's listing.

    Unlike the aggregate `Listing.views` counter (which counts every hit,
    including anonymous ones), this records *who* looked at a car so the
    dealer can follow up. We only create a row for authenticated viewers who
    are not the seller, and de-duplicate repeat views within a short window
    so one curious buyer does not flood the dealer's leads.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="view_leads"
    )
    listing_title = models.CharField(max_length=200)
    listing_price = models.CharField(max_length=40, blank=True, default="")

    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="listing_views", null=True, blank=True,
    )
    viewer_name = models.CharField(max_length=120, blank=True, default="")
    viewer_phone = models.CharField(max_length=15, blank=True, default="")
    viewer_email = models.EmailField(blank=True, null=True)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="listing_views_received", null=True, blank=True,
    )
    seller_name = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")

    view_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Listing view lead"
        verbose_name_plural = "Listing view leads"
        indexes = [
            models.Index(fields=["seller", "-updated_at"]),
            models.Index(fields=["listing", "viewer"]),
        ]

    def __str__(self) -> str:
        return f"{self.viewer_name or 'Guest'} viewed {self.listing_title}"


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


class LoanInquiry(models.Model):
    """A used-car loan application submitted from the public Loan section.

    Unlike :class:`Inquiry` (buyer ↔ seller about a listing), this captures a
    lead for our loan-assistance partners (Paisabazaar, BankBazaar, IndiaLends)
    against a selected bank. It is not tied to a listing.
    """

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Employment(models.TextChoices):
        SALARIED = "salaried", "Salaried"
        SELF_EMPLOYED = "self_employed", "Self-Employed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bank_name = models.CharField(max_length=80, db_index=True)
    loan_partner = models.CharField(max_length=80, db_index=True)

    full_name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=15, db_index=True)
    email = models.EmailField()
    city = models.CharField(max_length=80)

    monthly_income = models.PositiveIntegerField()
    employment_type = models.CharField(
        max_length=20,
        choices=Employment.choices,
        default=Employment.SALARIED,
    )
    car_budget = models.CharField(max_length=80, blank=True, default="")
    message = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Loan inquiry"
        verbose_name_plural = "Loan inquiries"

    def __str__(self) -> str:
        return f"{self.full_name} → {self.bank_name} ({self.loan_partner})"


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
