"""Admin operators, activity log, platform settings."""
import uuid
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Admin(models.Model):
    """Operator account for the admin panel."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "super-admin", "Super admin"
        MODERATOR = "moderator", "Moderator"
        SUPPORT = "support", "Support"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=200)
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MODERATOR
    )
    avatar_url = models.URLField(blank=True, default="")
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.role})"

    def set_password(self, raw: str) -> None:
        self.password_hash = make_password(raw)

    def check_password(self, raw: str) -> bool:
        return check_password(raw, self.password_hash)


class ActivityLog(models.Model):
    """Admin / system activity feed."""

    TYPE_CHOICES = [
        ("listing-approved", "Listing approved"),
        ("listing-rejected", "Listing rejected"),
        ("listing-featured", "Listing featured"),
        ("listing-unfeatured", "Listing unfeatured"),
        ("listing-blocked", "Listing blocked"),
        ("listing-deleted", "Listing deleted"),
        ("user-blocked", "User blocked"),
        ("user-unblocked", "User unblocked"),
        ("user-verified", "User verified"),
        ("admin-login", "Admin login"),
        ("settings-updated", "Settings updated"),
        ("dealer-offer-granted", "Dealer offer granted"),
        ("dealer-offer-updated", "Dealer offer updated"),
        ("dealer-offer-revoked", "Dealer offer revoked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_admin = models.ForeignKey(
        Admin, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activities",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    message = models.TextField()
    target = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"[{self.type}] {self.message}"


class AppSettings(models.Model):
    """Singleton platform settings (always id=1)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    auto_approve_listings = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=True)
    max_photos_per_listing = models.PositiveSmallIntegerField(default=12)
    min_listing_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=50000
    )
    max_listing_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=50000000
    )
    blocked_keywords = models.JSONField(
        default=list, blank=True
    )
    support_email = models.EmailField(default="support@oldcarbazar.com")
    support_phone = models.CharField(max_length=32, default="+91 91358 95389")
    # Business WhatsApp for concierge (sell/buy/loan/help). Digits-only with
    # country code is fine — the storefront normalises before opening wa.me.
    whatsapp_phone = models.CharField(max_length=32, default="919135895389")
    brand_color = models.CharField(max_length=16, default="#f75d34")
    loan_tools_content = models.JSONField(blank=True, null=True)
    # Dealer launch-offer campaign (title, duration default, max grants, etc.)
    dealer_offer = models.JSONField(blank=True, null=True)
    # Promotional ad banners shown across the website AND the mobile app.
    # Each entry is a plain dict (see web `lib/ads.ts` / app `lib/api.ts` Ad type).
    ads = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App settings"
        verbose_name_plural = "App settings"

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def singleton(cls) -> "AppSettings":
        obj, _ = cls.objects.get_or_create(
            id=1, defaults={"blocked_keywords": ["scam", "stolen", "lottery"]},
        )
        return obj

    def __str__(self) -> str:
        return "App settings"


class WhatsAppIntentLog(models.Model):
    """Tracks WhatsApp button taps from the storefront (concierge + seller contact)."""

    class Intent(models.TextChoices):
        SELL = "sell", "Sell via concierge"
        BUY = "buy", "Buy via concierge"
        LOAN = "loan", "Loan help"
        HELP = "help", "Support"
        SELLER_CONTACT = "seller_contact", "Contact listing seller"
        SHARE_LISTING = "share_listing", "Share listing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.CharField(max_length=32, choices=Intent.choices, db_index=True)
    listing_id = models.CharField(max_length=64, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    language = models.CharField(max_length=8, blank=True, default="en")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_intents",
    )
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"[{self.intent}] {self.created_at:%Y-%m-%d %H:%M}"
