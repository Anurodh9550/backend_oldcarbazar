from decimal import Decimal

from django.db.models import F
from rest_framework import serializers

from apps.listings.models import Listing
from .models import (
    ExpertRequest,
    Inquiry,
    LoanInquiry,
    Offer,
    PartnershipInquiry,
    TestDriveBooking,
)


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
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1")
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


# --------------------------------------------------------------------------- #
# Loan inquiries (public used-car loan applications)
# --------------------------------------------------------------------------- #


class LoanInquirySerializer(serializers.ModelSerializer):
    employment_type_label = serializers.CharField(
        source="get_employment_type_display", read_only=True
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = LoanInquiry
        fields = (
            "id",
            "bank_name",
            "loan_partner",
            "full_name",
            "mobile",
            "email",
            "city",
            "monthly_income",
            "employment_type",
            "employment_type_label",
            "car_budget",
            "message",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")


class CreateLoanInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanInquiry
        fields = (
            "bank_name",
            "loan_partner",
            "full_name",
            "mobile",
            "email",
            "city",
            "monthly_income",
            "employment_type",
            "car_budget",
            "message",
        )

    def validate_mobile(self, value):
        return _validate_indian_phone(value)

    def validate_full_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Please enter your full name.")
        return cleaned


class LoanInquiryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=LoanInquiry.Status.choices)


class PartnershipInquirySerializer(serializers.ModelSerializer):
    partnership_type_label = serializers.CharField(
        source="get_partnership_type_display", read_only=True
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = PartnershipInquiry
        fields = (
            "id",
            "business_name",
            "contact_person",
            "email",
            "phone",
            "partnership_type",
            "partnership_type_label",
            "message",
            "city",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")


class CreatePartnershipInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnershipInquiry
        fields = (
            "business_name",
            "contact_person",
            "email",
            "phone",
            "partnership_type",
            "message",
            "city",
        )

    def validate_phone(self, value):
        return _validate_indian_phone(value)

    def validate_business_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Please enter your business name.")
        return cleaned

    def validate_contact_person(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Please enter the contact person name.")
        return cleaned

    def validate_message(self, value):
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError(
                "Please tell us a bit more about your business."
            )
        return cleaned


class PartnershipInquiryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PartnershipInquiry.Status.choices)


class ExpertRequestSerializer(serializers.ModelSerializer):
    requirement_label = serializers.CharField(
        source="get_requirement_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)
    assigned_to_email = serializers.CharField(source="assigned_to.email", read_only=True)

    class Meta:
        model = ExpertRequest
        fields = (
            "id",
            "user",
            "name",
            "phone",
            "email",
            "city",
            "requirement",
            "requirement_label",
            "message",
            "status",
            "status_label",
            "assigned_to",
            "assigned_to_name",
            "assigned_to_email",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")


class CreateExpertRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    requirement = serializers.ChoiceField(choices=ExpertRequest.Requirement.choices)
    message = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        request = self.context["request"]
        if request.user.is_authenticated:
            attrs["name"] = attrs.get("name") or request.user.name
            attrs["phone"] = _validate_indian_phone(
                attrs.get("phone") or request.user.phone
            )
            attrs["email"] = attrs.get("email") or request.user.email
            attrs["city"] = attrs.get("city") or request.user.city or ""
            return attrs

        if not attrs.get("name", "").strip():
            raise serializers.ValidationError({"name": "Please enter your name."})
        if not attrs.get("phone", "").strip():
            raise serializers.ValidationError({"phone": "Please enter your phone."})
        if not attrs.get("city", "").strip():
            raise serializers.ValidationError({"city": "Please enter your city."})

        attrs["name"] = attrs["name"].strip()
        attrs["phone"] = _validate_indian_phone(attrs["phone"])
        attrs["city"] = attrs["city"].strip()
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return ExpertRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=validated_data["name"].strip(),
            phone=validated_data["phone"],
            email=(validated_data.get("email") or "").strip() or None,
            city=(validated_data.get("city") or "").strip(),
            requirement=validated_data["requirement"],
            message=(validated_data.get("message") or "").strip(),
        )
