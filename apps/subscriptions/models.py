"""Subscription records.

A `Subscription` row exists for every paid activation we have ever
recorded. The user's *current* plan is whichever row has the latest
`expires_at` that is still in the future. When that row expires the
user silently falls back to the implicit Free plan.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    """One paid plan activation."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        PENDING = "pending", "Pending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.CharField(max_length=32, db_index=True)
    amount_inr = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    # Payment-provider metadata. Razorpay / Stripe / manual will all fit
    # in here; we just record whatever proof we get so support can
    # reconcile a charge later.
    provider = models.CharField(max_length=24, blank=True, default="manual")
    provider_payment_id = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-expires_at",)
        indexes = [models.Index(fields=["user", "expires_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.plan} · {self.expires_at:%Y-%m-%d}"

    @property
    def is_currently_active(self) -> bool:
        return (
            self.status == self.Status.ACTIVE
            and self.expires_at > timezone.now()
        )


class RazorpayOrder(models.Model):
    """Server-side record of one Razorpay checkout order.

    Razorpay sends the order id back to the browser after payment. We keep a
    local copy so verification can prove which user and plan the payment was
    created for, instead of trusting browser-submitted plan details.
    """

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="razorpay_orders",
    )
    subscription = models.OneToOneField(
        Subscription,
        on_delete=models.SET_NULL,
        related_name="razorpay_order",
        null=True,
        blank=True,
    )
    plan = models.CharField(max_length=32, db_index=True)
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
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["plan", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.razorpay_order_id} · {self.user_id} · {self.plan}"
