from django.db.models import F
from rest_framework import serializers

from apps.listings.models import Listing
from .models import Inquiry


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
    listing = serializers.UUIDField()
    buyer_name = serializers.CharField(max_length=120)
    buyer_phone = serializers.CharField(max_length=15)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    message = serializers.CharField(min_length=3, max_length=1000)
    channel = serializers.ChoiceField(
        choices=Inquiry.Channel.choices, default=Inquiry.Channel.FORM
    )

    def create(self, validated):
        request = self.context["request"]
        try:
            listing = Listing.objects.get(pk=validated["listing"])
        except Listing.DoesNotExist as exc:
            raise serializers.ValidationError("Listing not found.") from exc

        inquiry = Inquiry.objects.create(
            listing=listing,
            listing_title=listing.title,
            listing_price=listing.price_label,
            buyer=request.user if request.user.is_authenticated else None,
            buyer_name=validated["buyer_name"],
            buyer_phone=validated["buyer_phone"],
            buyer_email=validated.get("buyer_email") or None,
            seller=listing.seller,
            seller_name=listing.seller_name,
            message=validated["message"],
            channel=validated["channel"],
            city=listing.location,
        )
        Listing.objects.filter(pk=listing.pk).update(
            inquiries_count=F("inquiries_count") + 1
        )
        return inquiry


class InquiryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Inquiry.Status.choices)
