from django.db.models import F
from rest_framework import serializers

from apps.listings.models import Listing
from .models import Inquiry, Offer, TestDriveBooking


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = (
            "id", "listing", "listing_title", "listing_price",
            "buyer", "buyer_name", "buyer_phone", "buyer_email",
            "seller", "seller_name",
            "message", "channel", "status", "city",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "listing_title", "listing_price",
            "seller", "seller_name", "buyer",
            "created_at", "updated_at",
        )


class CreateInquirySerializer(serializers.Serializer):
    """Minimal buyer-intent capture: only Name + Phone are required.

    Email and free-text message are optional. The buyer's intent is implied
    by the listing they submitted the form against.
    """
    listing = serializers.UUIDField()
    buyer_name = serializers.CharField(max_length=120)
    buyer_phone = serializers.CharField(max_length=15)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    message = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )
    channel = serializers.ChoiceField(
        choices=Inquiry.Channel.choices, default=Inquiry.Channel.FORM
    )

    def validate_buyer_phone(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())[-10:]
        if len(digits) != 10 or digits[0] not in "6789":
            raise serializers.ValidationError(
                "Enter a 10-digit Indian mobile number."
            )
        return digits

    def create(self, validated):
        request = self.context["request"]
        try:
            listing = Listing.objects.get(pk=validated["listing"])
        except Listing.DoesNotExist as exc:
            raise serializers.ValidationError("Listing not found.") from exc

        message = (validated.get("message") or "").strip()
        if not message:
            message = f"Interested in {listing.title}. Please call back."

        inquiry = Inquiry.objects.create(
            listing=listing,
            listing_title=listing.title,
            listing_price=listing.price_label,
            buyer=request.user if request.user.is_authenticated else None,
            buyer_name=validated["buyer_name"].strip(),
            buyer_phone=validated["buyer_phone"],
            buyer_email=validated.get("buyer_email") or None,
            seller=listing.seller,
            seller_name=listing.seller_name,
            message=message,
            channel=validated["channel"],
            city=listing.location,
        )
        Listing.objects.filter(pk=listing.pk).update(
            inquiries_count=F("inquiries_count") + 1
        )
        return inquiry


class InquiryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Inquiry.Status.choices)


# --------------------------------------------------------------------------- #
# Test drive bookings
# --------------------------------------------------------------------------- #


def _validate_indian_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())[-10:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise serializers.ValidationError(
            "Enter a 10-digit Indian mobile number."
        )
    return digits


class TestDriveBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestDriveBooking
        fields = (
            "id", "listing", "listing_title",
            "buyer", "buyer_name", "buyer_phone", "buyer_email",
            "seller",
            "scheduled_at", "location_note", "message",
            "status", "seller_response",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "listing_title", "buyer", "seller",
            "created_at", "updated_at",
        )


class CreateTestDriveSerializer(serializers.Serializer):
    listing = serializers.UUIDField()
    buyer_name = serializers.CharField(max_length=120)
    buyer_phone = serializers.CharField(max_length=15)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    scheduled_at = serializers.DateTimeField()
    location_note = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    message = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )

    def validate_buyer_phone(self, value):
        return _validate_indian_phone(value)

    def create(self, validated):
        request = self.context["request"]
        try:
            listing = Listing.objects.get(pk=validated["listing"])
        except Listing.DoesNotExist as exc:
            raise serializers.ValidationError("Listing not found.") from exc

        return TestDriveBooking.objects.create(
            listing=listing,
            listing_title=listing.title,
            buyer=request.user if request.user.is_authenticated else None,
            buyer_name=validated["buyer_name"].strip(),
            buyer_phone=validated["buyer_phone"],
            buyer_email=validated.get("buyer_email") or None,
            seller=listing.seller,
            scheduled_at=validated["scheduled_at"],
            location_note=(validated.get("location_note") or "").strip(),
            message=(validated.get("message") or "").strip(),
        )


class TestDriveStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TestDriveBooking.Status.choices)
    seller_response = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


# --------------------------------------------------------------------------- #
# Offers
# --------------------------------------------------------------------------- #


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = (
            "id", "listing", "listing_title", "listing_price_inr",
            "buyer", "buyer_name", "buyer_phone", "buyer_email",
            "seller",
            "amount", "counter_amount", "message", "seller_response",
            "status",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "listing_title", "listing_price_inr",
            "buyer", "seller",
            "created_at", "updated_at",
        )


class CreateOfferSerializer(serializers.Serializer):
    listing = serializers.UUIDField()
    buyer_name = serializers.CharField(max_length=120)
    buyer_phone = serializers.CharField(max_length=15)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    message = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )

    def validate_buyer_phone(self, value):
        return _validate_indian_phone(value)

    def create(self, validated):
        request = self.context["request"]
        try:
            listing = Listing.objects.get(pk=validated["listing"])
        except Listing.DoesNotExist as exc:
            raise serializers.ValidationError("Listing not found.") from exc

        return Offer.objects.create(
            listing=listing,
            listing_title=listing.title,
            listing_price_inr=listing.price_inr,
            buyer=request.user if request.user.is_authenticated else None,
            buyer_name=validated["buyer_name"].strip(),
            buyer_phone=validated["buyer_phone"],
            buyer_email=validated.get("buyer_email") or None,
            seller=listing.seller,
            amount=validated["amount"],
            message=(validated.get("message") or "").strip(),
        )


class OfferResponseSerializer(serializers.Serializer):
    """Seller-side response: accept / reject / counter."""
    status = serializers.ChoiceField(
        choices=[
            Offer.Status.ACCEPTED,
            Offer.Status.REJECTED,
            Offer.Status.COUNTERED,
        ]
    )
    counter_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    seller_response = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        if data["status"] == Offer.Status.COUNTERED and not data.get("counter_amount"):
            raise serializers.ValidationError(
                {"counter_amount": "Counter amount is required when countering."}
            )
        return data
