"""Serializers for Virtual Showroom + listing availability."""
from rest_framework import serializers

from apps.listings.models import Listing

from .dealer_tools import (
    DealerShowroom,
    ListingAvailability,
    ShowroomGalleryItem,
    ShowroomReview,
    ShowroomTeamMember,
)
from .models import User


class ShowroomTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowroomTeamMember
        fields = ("id", "name", "role", "photo_url", "bio", "sort_order")


class ShowroomReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowroomReview
        fields = ("id", "author", "rating", "text", "review_date", "created_at")
        read_only_fields = ("id", "created_at")


class ShowroomGalleryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowroomGalleryItem
        fields = ("id", "title", "photo_url", "price_label", "note", "sort_order")


class DealerShowroomSerializer(serializers.ModelSerializer):
    dealer_id = serializers.UUIDField(source="dealer.id", read_only=True)
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    team = ShowroomTeamMemberSerializer(many=True, required=False)
    reviews = ShowroomReviewSerializer(many=True, required=False)
    gallery = ShowroomGalleryItemSerializer(many=True, required=False)

    class Meta:
        model = DealerShowroom
        fields = (
            "dealer_id",
            "dealer_name",
            "enabled",
            "banner_url",
            "logo_url",
            "tagline",
            "about",
            "address",
            "whatsapp",
            "team",
            "reviews",
            "gallery",
            "updated_at",
        )
        read_only_fields = ("dealer_id", "dealer_name", "updated_at")

    def _sync_nested(self, showroom, team_data, reviews_data, gallery_data):
        if team_data is not None:
            showroom.team.all().delete()
            ShowroomTeamMember.objects.bulk_create(
                [
                    ShowroomTeamMember(
                        showroom=showroom,
                        **{k: v for k, v in item.items() if k != "id"},
                    )
                    for item in team_data
                ]
            )
        if reviews_data is not None:
            showroom.reviews.all().delete()
            ShowroomReview.objects.bulk_create(
                [
                    ShowroomReview(
                        showroom=showroom,
                        **{k: v for k, v in item.items() if k != "id"},
                    )
                    for item in reviews_data
                ]
            )
        if gallery_data is not None:
            showroom.gallery.all().delete()
            ShowroomGalleryItem.objects.bulk_create(
                [
                    ShowroomGalleryItem(
                        showroom=showroom,
                        **{k: v for k, v in item.items() if k != "id"},
                    )
                    for item in gallery_data
                ]
            )

    def create(self, validated_data):
        team_data = validated_data.pop("team", None)
        reviews_data = validated_data.pop("reviews", None)
        gallery_data = validated_data.pop("gallery", None)
        showroom = DealerShowroom.objects.create(**validated_data)
        self._sync_nested(showroom, team_data, reviews_data, gallery_data)
        return showroom

    def update(self, instance, validated_data):
        team_data = validated_data.pop("team", None)
        reviews_data = validated_data.pop("reviews", None)
        gallery_data = validated_data.pop("gallery", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._sync_nested(instance, team_data, reviews_data, gallery_data)
        return instance


class ListingAvailabilitySerializer(serializers.ModelSerializer):
    listing_id = serializers.UUIDField(source="listing.id", read_only=True)
    title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ListingAvailability
        fields = (
            "listing_id",
            "title",
            "status",
            "note",
            "available_from",
            "updated_at",
        )
        read_only_fields = ("listing_id", "title", "updated_at")


class ListingAvailabilityUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ListingAvailability.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    available_from = serializers.DateField(required=False, allow_null=True)

    def save_for_listing(self, listing: Listing, dealer: User) -> ListingAvailability:
        if listing.seller_id != dealer.id:
            raise serializers.ValidationError("Not your listing.")
        data = self.validated_data
        obj, _ = ListingAvailability.objects.update_or_create(
            listing=listing,
            defaults={
                "dealer": dealer,
                "status": data["status"],
                "note": data.get("note", ""),
                "available_from": data.get("available_from"),
            },
        )
        return obj
