"""Listings API."""
import logging

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.db.models import F
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from apps.adminpanel.models import ActivityLog
from apps.adminpanel.permissions import IsAdminOperator
from .filters import ListingFilter
from .models import Listing
from .permissions import IsOwnerOrAdminOrReadOnly
from .serializers import (
    CreateListingSerializer,
    FeatureSerializer,
    FlagSerializer,
    ListingSerializer,
    MediaUploadSerializer,
    ModerationSerializer,
    UpdateListingSerializer,
    UpdateStatusSerializer,
)


class ListingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Public listings API.

    - GET   /api/v1/listings/              list (filters: city, brand, fuel, …)
    - GET   /api/v1/listings/<id>/         detail (auto-increments views)
    - POST  /api/v1/listings/              create (auth required, becomes seller)
    - PATCH /api/v1/listings/<id>/         owner/admin partial update
    - PUT   /api/v1/listings/<id>/         owner/admin full update
    - DEL   /api/v1/listings/<id>/         owner/admin delete
    - POST  /api/v1/listings/<id>/status/  owner status update (active|sold|draft)
    - GET   /api/v1/listings/mine/         current user's listings
    """
    queryset = Listing.objects.prefetch_related("photos").all()
    permission_classes = (IsOwnerOrAdminOrReadOnly,)
    filterset_class = ListingFilter
    search_fields = ("title", "brand", "model", "location", "description")
    ordering_fields = ("created_at", "price_inr", "kms", "views")
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "create":
            return CreateListingSerializer
        if self.action in ("update", "partial_update"):
            return UpdateListingSerializer
        return ListingSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        updated = ser.save()
        return Response(ListingSerializer(updated).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        # Admin list endpoint sees everything if explicitly asked.
        if self.action == "list" and not self.request.query_params.get("moderation"):
            qs = qs.filter(
                moderation=Listing.Moderation.APPROVED,
                status=Listing.Status.ACTIVE,
            )
        return qs

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Login required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        listing = ser.save()
        return Response(
            ListingSerializer(listing).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Listing.objects.filter(pk=instance.pk).update(views=F("views") + 1)
        instance.refresh_from_db(fields=["views"])
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        qs = Listing.objects.filter(seller=request.user).prefetch_related("photos")
        page = self.paginate_queryset(qs)
        ser = ListingSerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="media-config",
        permission_classes=[permissions.AllowAny],
    )
    def media_config(self, request):
        """Public diagnostic: is Cloudinary set up on the server?"""
        cfg = cloudinary.config()
        return Response({
            "configured": bool(cfg.cloud_name and cfg.api_key and cfg.api_secret),
            "cloud_name_set": bool(cfg.cloud_name),
            "api_key_set": bool(cfg.api_key),
            "api_secret_set": bool(cfg.api_secret),
        })

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-media",
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_media(self, request):
        """Upload a photo/video to Cloudinary and return the hosted URL."""
        cfg = cloudinary.config()
        if not (cfg.cloud_name and cfg.api_key and cfg.api_secret):
            logger.error(
                "Cloudinary env vars missing: cloud_name=%s api_key_set=%s api_secret_set=%s",
                cfg.cloud_name,
                bool(cfg.api_key),
                bool(cfg.api_secret),
            )
            return Response(
                {
                    "detail": (
                        "Server is not configured for media uploads. "
                        "Admin needs to set CLOUDINARY_CLOUD_NAME, "
                        "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ser = MediaUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        uploaded_file = ser.validated_data["file"]
        folder = ser.validated_data["folder"]

        try:
            result = cloudinary.uploader.upload(
                uploaded_file,
                folder=folder,
                resource_type="auto",
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )
        except CloudinaryError as exc:
            logger.exception("Cloudinary upload failed for user %s", request.user.pk)
            return Response(
                {"detail": f"Cloudinary upload failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:  # pragma: no cover — surface unexpected errors
            logger.exception("Unexpected upload error for user %s", request.user.pk)
            return Response(
                {"detail": f"Unexpected upload error: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "url": result.get("secure_url"),
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "resource_type": result.get("resource_type"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "width": result.get("width"),
                "height": result.get("height"),
                "duration": result.get("duration"),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="status", permission_classes=[permissions.IsAuthenticated])
    def set_status(self, request, pk=None):
        listing = self.get_object()
        if listing.seller_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Not your listing"}, status=403)
        ser = UpdateStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        listing.status = ser.validated_data["status"]
        listing.save(update_fields=["status", "updated_at"])
        return Response(ListingSerializer(listing).data)

    # ----------- Admin-only moderation actions ----------- #

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOperator])
    def moderate(self, request, pk=None):
        listing = self.get_object()
        ser = ModerationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_status = ser.validated_data["status"]
        reason = ser.validated_data.get("reason", "")
        listing.moderation = new_status
        listing.rejected_reason = reason if new_status in (
            Listing.Moderation.REJECTED, Listing.Moderation.BLOCKED
        ) else ""
        listing.save(update_fields=["moderation", "rejected_reason", "updated_at"])

        ActivityLog.objects.create(
            actor_admin=request.user.admin_profile if hasattr(request.user, "admin_profile") else None,
            type=(
                "listing-rejected" if new_status == "rejected" else
                "listing-blocked" if new_status == "blocked" else
                "listing-approved"
            ),
            message=f"Moderation → {new_status}" + (f": {reason}" if reason else ""),
            target=str(listing.id),
        )
        return Response(ListingSerializer(listing).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOperator])
    def feature(self, request, pk=None):
        listing = self.get_object()
        ser = FeatureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        listing.featured = ser.validated_data["featured"]
        listing.save(update_fields=["featured", "updated_at"])
        ActivityLog.objects.create(
            type="listing-featured" if listing.featured else "listing-unfeatured",
            message=("Marked featured" if listing.featured else "Removed featured"),
            target=str(listing.id),
        )
        return Response(ListingSerializer(listing).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOperator])
    def flag(self, request, pk=None):
        listing = self.get_object()
        ser = FlagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        listing.flagged = True
        listing.flag_reason = ser.validated_data["reason"]
        listing.save(update_fields=["flagged", "flag_reason", "updated_at"])
        return Response(ListingSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="clear-flag",
            permission_classes=[IsAdminOperator])
    def clear_flag(self, request, pk=None):
        listing = self.get_object()
        listing.flagged = False
        listing.flag_reason = ""
        listing.save(update_fields=["flagged", "flag_reason", "updated_at"])
        return Response(ListingSerializer(listing).data)
