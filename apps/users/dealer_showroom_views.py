"""API views for Virtual Showroom + Car Availability."""
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing

from .dealer_showroom_serializers import (
    DealerShowroomSerializer,
    ListingAvailabilitySerializer,
    ListingAvailabilityUpdateSerializer,
)
from .dealer_tools import DealerShowroom, ListingAvailability
from .models import User


def _seller_only(user) -> bool:
    return user.is_authenticated and user.role in (
        User.Role.SELLER,
        User.Role.BOTH,
    )


class DealerShowroomPublicView(APIView):
    """GET /api/v1/dealers/<uuid>/showroom/"""

    permission_classes = (permissions.AllowAny,)

    def get(self, request, dealer_id):
        showroom = get_object_or_404(
            DealerShowroom.objects.select_related("dealer").prefetch_related(
                "team", "reviews", "gallery"
            ),
            dealer_id=dealer_id,
            enabled=True,
        )
        data = DealerShowroomSerializer(showroom).data
        data["phone"] = showroom.dealer.phone
        return Response(data)


class MyDealerShowroomView(APIView):
    """GET / PATCH /api/v1/dealers/me/showroom/"""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        if not _seller_only(request.user):
            return Response(
                {"detail": "Seller account required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        showroom, _ = DealerShowroom.objects.get_or_create(
            dealer=request.user,
            defaults={
                "tagline": "Your trusted used car partner",
                "about": "",
            },
        )
        showroom = (
            DealerShowroom.objects.filter(pk=showroom.pk)
            .prefetch_related("team", "reviews", "gallery")
            .first()
        )
        return Response(DealerShowroomSerializer(showroom).data)

    def patch(self, request):
        if not _seller_only(request.user):
            return Response(
                {"detail": "Seller account required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        showroom, _ = DealerShowroom.objects.get_or_create(dealer=request.user)
        ser = DealerShowroomSerializer(
            showroom, data=request.data, partial=True
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class MyListingAvailabilityView(APIView):
    """GET /api/v1/dealers/me/availability/"""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        if not _seller_only(request.user):
            return Response(
                {"detail": "Seller account required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = (
            ListingAvailability.objects.filter(dealer=request.user)
            .select_related("listing")
            .order_by("-updated_at")
        )
        return Response(ListingAvailabilitySerializer(qs, many=True).data)


class ListingAvailabilityDetailView(APIView):
    """PATCH /api/v1/dealers/me/availability/<listing_id>/"""

    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, listing_id):
        if not _seller_only(request.user):
            return Response(
                {"detail": "Seller account required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        listing = get_object_or_404(Listing, id=listing_id)
        ser = ListingAvailabilityUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = ser.save_for_listing(listing, request.user)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(ListingAvailabilitySerializer(obj).data)


class DealerListingAvailabilityPublicView(APIView):
    """GET /api/v1/dealers/<uuid>/availability/ — public map for showroom."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request, dealer_id):
        qs = (
            ListingAvailability.objects.filter(dealer_id=dealer_id)
            .select_related("listing")
            .order_by("-updated_at")
        )
        return Response(ListingAvailabilitySerializer(qs, many=True).data)
