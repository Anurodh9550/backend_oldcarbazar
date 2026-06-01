"""Serializers for subscription endpoints."""
from rest_framework import serializers

from .plans import FREE_LISTING_LIMIT
from .models import Subscription


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


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id", "plan", "amount_inr", "status",
            "started_at", "expires_at",
            "provider", "provider_payment_id",
            "created_at", "updated_at",
        )
        read_only_fields = fields
