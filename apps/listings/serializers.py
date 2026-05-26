"""Serializers for listings + photos."""
import re
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import serializers

from .models import Listing, ListingPhoto


MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class ListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ("id", "url", "position", "is_cover")
        read_only_fields = ("id",)


class MediaUploadSerializer(serializers.Serializer):
    """Validates photo/video uploads before sending the file to Cloudinary."""

    file = serializers.FileField()
    folder = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default="old-car-bazar"
    )

    def validate_file(self, file):
        content_type = getattr(file, "content_type", "")
        if content_type in ALLOWED_IMAGE_CONTENT_TYPES:
            max_bytes = MAX_IMAGE_UPLOAD_BYTES
        elif content_type in ALLOWED_VIDEO_CONTENT_TYPES:
            max_bytes = MAX_VIDEO_UPLOAD_BYTES
        else:
            raise serializers.ValidationError(
                "Only JPG, PNG, WEBP, MP4, MOV and WEBM uploads are allowed."
            )

        if file.size > max_bytes:
            size_mb = max_bytes // (1024 * 1024)
            raise serializers.ValidationError(
                f"File is too large. Maximum allowed size is {size_mb} MB."
            )
        return file

    def validate_folder(self, folder):
        folder = (folder or "old-car-bazar").strip().strip("/")
        if not folder:
            return "old-car-bazar"
        if ".." in folder or "\\" in folder:
            raise serializers.ValidationError("Invalid folder name.")
        return folder


class ListingSerializer(serializers.ModelSerializer):
    """Read-only output serializer (with nested photos + seller name)."""
    photos = ListingPhotoSerializer(many=True, read_only=True)
    seller_id = serializers.UUIDField(source="seller.id", read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id", "seller_id", "seller_name", "seller_phone", "seller_email",
            "title", "brand", "model", "variant", "year",
            "price_label", "price_inr",
            "kms", "fuel", "transmission", "owners", "ownership",
            "body_type", "color", "seats", "engine_cc", "mileage",
            "registration_month", "reg_number", "insurance",
            "location", "area",
            "description", "features",
            "cover_image", "photos",
            "status", "moderation", "rejected_reason",
            "featured", "flagged", "flag_reason",
            "whatsapp", "is_seed",
            "views", "inquiries_count",
            "created_at", "updated_at",
        )
        read_only_fields = fields


# ---------- Write serializers ---------- #

def _lakhs_to_inr(label: str) -> Decimal:
    """`12.5` → 1250000 INR."""
    try:
        n = Decimal(str(label).strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")
    return (n * Decimal("100000")).quantize(Decimal("1.00"))


def _format_price_label(label: str) -> str:
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*$", str(label))
    if not m:
        return label
    n = float(m.group(1))
    if n >= 100:
        return f"₹{n/100:.2f} Cr"
    return f"₹{n} Lakh"


class CreateListingSerializer(serializers.Serializer):
    """Input shape matches the front-end `SellCarFormData`."""
    brand = serializers.CharField(max_length=80)
    model = serializers.CharField(max_length=120)
    variant = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    year = serializers.IntegerField(min_value=1990, max_value=timezone.now().year + 1)
    body_type = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    color = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    fuel = serializers.CharField(max_length=24)
    transmission = serializers.CharField(max_length=24)
    kms = serializers.IntegerField(min_value=0, max_value=1_000_000)
    owners = serializers.CharField(max_length=32)
    seats = serializers.IntegerField(min_value=2, max_value=20, default=5)
    registration_month = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    engine_cc = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    mileage = serializers.CharField(max_length=24, required=False, allow_blank=True, default="")
    insurance = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    price = serializers.CharField(max_length=40)  # in lakhs
    city = serializers.CharField(max_length=80)
    area = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    reg_number = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    features = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, default=list
    )
    seller_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    whatsapp = serializers.BooleanField(default=True)
    photos = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )

    def create(self, validated):
        from apps.adminpanel.models import AppSettings
        settings_row = AppSettings.singleton()
        auto_approve = settings_row.auto_approve_listings
        request = self.context["request"]
        user = request.user

        ownership_map = {
            "1st Owner": "First owner",
            "2nd Owner": "Second owner",
            "3rd Owner": "Third owner",
        }

        title = f"{validated['year']} {validated['brand']} {validated['model']}"
        if validated.get("variant"):
            title += f" {validated['variant']}"

        listing = Listing.objects.create(
            seller=user,
            seller_name=validated["seller_name"],
            seller_phone=validated["phone"],
            seller_email=validated.get("email") or user.email,
            title=title.strip(),
            brand=validated["brand"],
            model=validated["model"],
            variant=validated.get("variant", ""),
            year=validated["year"],
            price_label=_format_price_label(validated["price"]),
            price_inr=_lakhs_to_inr(validated["price"]),
            kms=validated["kms"],
            fuel=validated["fuel"],
            transmission=validated["transmission"],
            owners=validated["owners"],
            ownership=ownership_map.get(validated["owners"], "Fourth owner & above"),
            seats=validated.get("seats", 5),
            body_type=validated.get("body_type", ""),
            color=validated.get("color", ""),
            engine_cc=validated.get("engine_cc", ""),
            mileage=validated.get("mileage", ""),
            registration_month=validated.get("registration_month", ""),
            reg_number=validated.get("reg_number", ""),
            insurance=validated.get("insurance", ""),
            location=validated["city"],
            area=validated.get("area", ""),
            description=validated.get("description", ""),
            features=validated.get("features", []),
            cover_image=(validated.get("photos") or [""])[0],
            status=Listing.Status.ACTIVE,
            moderation=Listing.Moderation.APPROVED
                if auto_approve else Listing.Moderation.PENDING,
            whatsapp=validated.get("whatsapp", True),
        )

        ListingPhoto.objects.bulk_create([
            ListingPhoto(
                listing=listing, url=url, position=i, is_cover=(i == 0)
            )
            for i, url in enumerate(validated.get("photos", []))
        ])

        user.promote_to_seller()
        return listing


class UpdateListingSerializer(serializers.Serializer):
    """Partial update for an existing listing (owner-only).

    Mirrors `CreateListingSerializer` but every field is optional so PATCH
    callers can send just the fields they changed.
    """
    brand = serializers.CharField(max_length=80, required=False)
    model = serializers.CharField(max_length=120, required=False)
    variant = serializers.CharField(max_length=120, required=False, allow_blank=True)
    year = serializers.IntegerField(
        min_value=1990, max_value=timezone.now().year + 1, required=False
    )
    body_type = serializers.CharField(max_length=32, required=False, allow_blank=True)
    color = serializers.CharField(max_length=32, required=False, allow_blank=True)
    fuel = serializers.CharField(max_length=24, required=False)
    transmission = serializers.CharField(max_length=24, required=False)
    kms = serializers.IntegerField(min_value=0, max_value=1_000_000, required=False)
    owners = serializers.CharField(max_length=32, required=False)
    seats = serializers.IntegerField(min_value=2, max_value=20, required=False)
    registration_month = serializers.CharField(
        max_length=16, required=False, allow_blank=True
    )
    engine_cc = serializers.CharField(max_length=16, required=False, allow_blank=True)
    mileage = serializers.CharField(max_length=24, required=False, allow_blank=True)
    insurance = serializers.CharField(max_length=64, required=False, allow_blank=True)
    price = serializers.CharField(max_length=40, required=False)
    city = serializers.CharField(max_length=80, required=False)
    area = serializers.CharField(max_length=120, required=False, allow_blank=True)
    reg_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )
    features = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False
    )
    seller_name = serializers.CharField(max_length=120, required=False)
    phone = serializers.CharField(max_length=15, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    whatsapp = serializers.BooleanField(required=False)
    photos = serializers.ListField(child=serializers.URLField(), required=False)

    OWNERSHIP_MAP = {
        "1st Owner": "First owner",
        "2nd Owner": "Second owner",
        "3rd Owner": "Third owner",
    }

    DIRECT_FIELDS = {
        "brand": "brand",
        "model": "model",
        "variant": "variant",
        "year": "year",
        "body_type": "body_type",
        "color": "color",
        "fuel": "fuel",
        "transmission": "transmission",
        "kms": "kms",
        "seats": "seats",
        "registration_month": "registration_month",
        "engine_cc": "engine_cc",
        "mileage": "mileage",
        "insurance": "insurance",
        "area": "area",
        "reg_number": "reg_number",
        "description": "description",
        "features": "features",
        "seller_name": "seller_name",
        "whatsapp": "whatsapp",
    }

    def update(self, instance, validated):
        for src, dest in self.DIRECT_FIELDS.items():
            if src in validated:
                setattr(instance, dest, validated[src])

        if "owners" in validated:
            instance.owners = validated["owners"]
            instance.ownership = self.OWNERSHIP_MAP.get(
                validated["owners"], "Fourth owner & above"
            )

        if "price" in validated:
            instance.price_label = _format_price_label(validated["price"])
            instance.price_inr = _lakhs_to_inr(validated["price"])

        if "city" in validated:
            instance.location = validated["city"]

        if "phone" in validated:
            instance.seller_phone = validated["phone"]

        if "email" in validated:
            instance.seller_email = validated["email"] or None

        if any(k in validated for k in ("year", "brand", "model", "variant")):
            title = f"{instance.year} {instance.brand} {instance.model}"
            if instance.variant:
                title += f" {instance.variant}"
            instance.title = title.strip()

        instance.save()

        if "photos" in validated:
            new_urls = validated["photos"]
            instance.photos.all().delete()
            ListingPhoto.objects.bulk_create([
                ListingPhoto(
                    listing=instance, url=url, position=i, is_cover=(i == 0)
                )
                for i, url in enumerate(new_urls)
            ])
            instance.cover_image = (new_urls or [""])[0]
            instance.save(update_fields=["cover_image", "updated_at"])

        return instance


class ModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Listing.Moderation.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class FeatureSerializer(serializers.Serializer):
    featured = serializers.BooleanField()


class FlagSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1, max_length=300)


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Listing.Status.choices)
