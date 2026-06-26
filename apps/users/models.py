"""User and OTP models."""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import UserManager


PHONE_VALIDATOR = RegexValidator(
    regex=r"^[6-9]\d{9}$",
    message="Indian phone must be 10 digits starting with 6-9.",
)


class User(AbstractBaseUser, PermissionsMixin):
    """End-user account (buyer / seller / both)."""

    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"
        BOTH = "both", "Buyer + Seller"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(
        max_length=15, unique=True, validators=[PHONE_VALIDATOR]
    )
    city = models.CharField(max_length=80, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")

    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.BUYER
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    admin_note = models.TextField(blank=True, default="")
    login_count = models.PositiveIntegerField(default=0)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class SellerResponseTier(models.TextChoices):
        NEW = "new", "New seller"
        FAST = "fast", "Fast responder"
        GOOD = "good", "Good responder"
        SLOW = "slow", "Slow responder"

    seller_avg_response_hours = models.FloatField(null=True, blank=True)
    seller_response_tier = models.CharField(
        max_length=10,
        choices=SellerResponseTier.choices,
        default=SellerResponseTier.NEW,
        db_index=True,
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ("-date_joined",)
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"

    @property
    def is_blocked(self) -> bool:
        return self.status == self.Status.BLOCKED

    def promote_to_seller(self) -> None:
        if self.role == self.Role.BUYER:
            self.role = self.Role.SELLER
        elif self.role == self.Role.SELLER:
            return
        else:
            self.role = self.Role.BOTH
        self.save(update_fields=["role", "updated_at"])


class OtpCode(models.Model):
    """One-time password (signup / reset / verify)."""

    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Signup"
        RESET = "reset", "Reset"
        VERIFY = "verify", "Verify"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.CharField(max_length=200, db_index=True)
    code = models.CharField(max_length=8)
    purpose = models.CharField(max_length=12, choices=Purpose.choices)
    consumed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"OTP for {self.target} ({self.purpose})"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()
