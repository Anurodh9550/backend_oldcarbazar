"""Serializers for subscription endpoints."""
from rest_framework import serializers

from apps.billing.gst import is_valid_gstin, normalize_gstin

from .plans import FREE_LISTING_LIMIT
from .models import Subscription


def validate_optional_gstin(value: str) -> str:
    """Allow blank, else require a structurally valid 15-char GSTIN."""
    value = normalize_gstin(value)
    if value and not is_valid_gstin(value):
        raise serializers.ValidationError(
            "Enter a valid 15-character GST number (e.g. 09ABCDE1234F1Z5)."
        )
    return value


class PlanSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    price_inr = serializers.IntegerField()
    duration_days = serializers.IntegerField()
    listing_limit = serializers.IntegerField(allow_null=True)
    perks = serializers.ListField(child=serializers.CharField())


class SubscriptionStatusSerializer(serializers.Serializer):
    plan = serializers.CharField()
    plan_name = serializers.CharField()
    listings_used = serializers.IntegerField()
    listings_limit = serializers.IntegerField(allow_null=True)
    is_unlimited = serializers.BooleanField()
    can_publish = serializers.BooleanField()
    started_at = serializers.DateTimeField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    free_listing_limit = serializers.IntegerField(default=FREE_LISTING_LIMIT)


class ActivateSubscriptionSerializer(serializers.Serializer):
    """Lightweight activation used by the demo/manual flow.

    A real payment integration (Razorpay etc.) will eventually call
    `services.activate_subscription` from inside its webhook handler
    after verifying the gateway signature. Until then, this endpoint
    is gated by `SUBSCRIPTION_ALLOW_DEMO_ACTIVATION` so we don't ship
    a free-upgrade button to production by accident.
    """
    plan = serializers.CharField()
    provider_payment_id = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class CreateRazorpayOrderSerializer(serializers.Serializer):
    plan = serializers.CharField()
    customer_gstin = serializers.CharField(
        required=False, allow_blank=True, default="",
        validators=[validate_optional_gstin],
    )

    def validate_customer_gstin(self, value):
        return validate_optional_gstin(value)


class RazorpayOrderSerializer(serializers.Serializer):
    key_id = serializers.CharField()
    order_id = serializers.CharField()
    amount = serializers.IntegerField()
    amount_inr = serializers.IntegerField()
    base_inr = serializers.IntegerField()
    gst_inr = serializers.IntegerField()
    gst_rate = serializers.IntegerField()
    seller_gstin = serializers.CharField()
    customer_gstin = serializers.CharField(allow_blank=True)
    currency = serializers.CharField()
    plan = PlanSerializer()
    name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, allow_null=True)
    contact = serializers.CharField()


class VerifyRazorpayPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id", "plan", "amount_inr", "base_inr", "gst_inr",
            "customer_gstin", "status",
            "started_at", "expires_at",
            "provider", "provider_payment_id",
            "created_at", "updated_at",
        )
        read_only_fields = fields
