"""Listings API."""
import logging
import uuid
from datetime import timedelta

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.conf import settings as dj_settings
from django.db.models import BooleanField, Case, F, Value, When
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from apps.adminpanel.models import ActivityLog
from apps.adminpanel.permissions import IsAdminOperator
from apps.subscriptions.services import can_publish
from .boost import BOOST_PACKAGES, get_boost_package
from .filters import ListingFilter
from .models import Listing, ListingBoostOrder
from .permissions import IsOwnerOrAdminOrReadOnly
from .serializers import (
    BoostOrderResponseSerializer,
    BoostPackageSerializer,
    CreateBoostOrderSerializer,
    CreateListingSerializer,
    FeatureSerializer,
    FlagSerializer,
    ListingSerializer,
    MediaUploadSerializer,
    ModerationSerializer,
    UpdateListingSerializer,
    UpdateStatusSerializer,
    VerifyBoostPaymentSerializer,
)


def _razorpay_configured() -> bool:
    return bool(dj_settings.RAZORPAY_KEY_ID and dj_settings.RAZORPAY_KEY_SECRET)


def _razorpay_client():
    """Return an authenticated Razorpay client or raise a clear error."""
    if not _razorpay_configured():
        raise RuntimeError("Razorpay keys are not configured.")
    try:
        import razorpay
    except ImportError as exc:  # pragma: no cover - dependency/runtime guard
        raise RuntimeError("Razorpay SDK is not installed.") from exc
    return razorpay.Client(
        auth=(dj_settings.RAZORPAY_KEY_ID, dj_settings.RAZORPAY_KEY_SECRET)
    )


def _gateway_not_configured_response():
    return Response(
        {
            "detail": (
                "Payments are not configured yet. Add Razorpay keys "
                "on the backend and redeploy."
            ),
            "code": "gateway_not_configured",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
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
    ordering_fields = (
        "featured",
        "inquiries_count",
        "views",
        "created_at",
        "price_inr",
        "kms",
    )
    ordering = (
        "-featured",
        "-boost_active",
        "-inquiries_count",
        "-views",
        "-created_at",
    )

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
        # Annotate paid-boost state so the default ordering can rank active
        # boosts just below admin-pinned featured cars. (A model property
        # can't be used in order_by, so we mirror it as a DB expression.)
        # NOTE: annotation name must NOT clash with the model's `is_boosted`
        # property (a property is a data descriptor and would raise when Django
        # tries to set the annotated value on each instance).
        qs = qs.annotate(
            boost_active=Case(
                When(boosted_until__gt=timezone.now(), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
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

        # Free-tier quota check. Once the seller is at the limit we
        # block the create (instead of letting it succeed and silently
        # putting them above the cap) and return the quota info so the
        # frontend can render an Upgrade modal without another fetch.
        allowed, quota = can_publish(request.user)
        if not allowed:
            return Response(
                {
                    "detail": (
                        f"You have reached the free plan limit of "
                        f"{quota['listings_limit']} active listings. "
                        f"Upgrade to {quota['plan_name']} to post more."
                    ),
                    "code": "subscription_required",
                    "subscription": quota,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
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

    # ----------------- Paid boost actions ----------------- #

    @action(
        detail=False,
        methods=["get"],
        url_path="boost-packages",
        permission_classes=[permissions.AllowAny],
    )
    def boost_packages(self, request):
        """Public list of paid boost packages."""
        data = [
            BoostPackageSerializer(p.to_dict()).data
            for p in BOOST_PACKAGES.values()
        ]
        return Response({"packages": data})

    @action(
        detail=True,
        methods=["post"],
        url_path="create-boost-order",
        permission_classes=[permissions.IsAuthenticated],
    )
    def create_boost_order(self, request, pk=None):
        """Create a Razorpay order to boost this listing."""
        listing = self.get_object()
        if listing.seller_id != request.user.id and not request.user.is_staff:
            return Response(
                {"detail": "You can only boost your own listing."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = CreateBoostOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pkg = get_boost_package(ser.validated_data["package"])
        if not pkg:
            return Response(
                {"detail": "Unknown boost package."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client = _razorpay_client()
        except RuntimeError:
            return _gateway_not_configured_response()

        receipt = f"ocbb_{request.user.id.hex[:10]}_{uuid.uuid4().hex[:10]}"
        amount_paise = pkg.price_inr * 100
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "user_id": str(request.user.id),
                "listing_id": str(listing.id),
                "package": pkg.code,
                "product": "old-car-bazar-boost",
            },
        }

        try:
            order = client.order.create(data=payload)
        except Exception as exc:  # pragma: no cover - provider/network error
            return Response(
                {
                    "detail": f"Could not create Razorpay order: {exc}",
                    "code": "razorpay_order_failed",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        ListingBoostOrder.objects.create(
            user=request.user,
            listing=listing,
            package=pkg.code,
            duration_days=pkg.duration_days,
            amount_inr=pkg.price_inr,
            razorpay_order_id=order["id"],
            receipt=receipt,
            raw_response=order,
        )

        data = {
            "key_id": dj_settings.RAZORPAY_KEY_ID,
            "order_id": order["id"],
            "amount": amount_paise,
            "amount_inr": pkg.price_inr,
            "currency": "INR",
            "package": pkg.to_dict(),
            "listing_id": str(listing.id),
            "name": request.user.name,
            "email": request.user.email or "",
            "contact": request.user.phone,
        }
        return Response(
            BoostOrderResponseSerializer(data).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="verify-boost-payment",
        permission_classes=[permissions.IsAuthenticated],
    )
    def verify_boost_payment(self, request, pk=None):
        """Verify Razorpay response and activate the boost on this listing."""
        listing = self.get_object()
        ser = VerifyBoostPaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        order = (
            ListingBoostOrder.objects
            .filter(
                user=request.user,
                listing=listing,
                razorpay_order_id=data["razorpay_order_id"],
            )
            .first()
        )
        if not order:
            return Response(
                {"detail": "Boost order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if order.status == ListingBoostOrder.Status.PAID:
            return Response(self.get_serializer(listing).data)

        try:
            client = _razorpay_client()
        except RuntimeError:
            return _gateway_not_configured_response()

        signature_payload = {
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        }
        try:
            client.utility.verify_payment_signature(signature_payload)
            payment = client.payment.fetch(data["razorpay_payment_id"])
        except Exception as exc:
            order.status = ListingBoostOrder.Status.FAILED
            order.raw_response = {
                **(order.raw_response or {}),
                "verification_error": str(exc),
            }
            order.save(update_fields=["status", "raw_response", "updated_at"])
            return Response(
                {
                    "detail": "Payment signature verification failed.",
                    "code": "payment_verification_failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            payment.get("order_id") != order.razorpay_order_id
            or payment.get("amount") != order.amount_inr * 100
        ):
            order.status = ListingBoostOrder.Status.FAILED
            order.raw_response = {
                **(order.raw_response or {}),
                "payment": payment,
                "verification_error": "amount_or_order_mismatch",
            }
            order.save(update_fields=["status", "raw_response", "updated_at"])
            return Response(
                {
                    "detail": "Payment amount/order did not match.",
                    "code": "payment_mismatch",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Stack the boost: if the listing is still boosted, extend from its
        # current end date; otherwise start the window from now.
        now = timezone.now()
        base = (
            listing.boosted_until
            if listing.boosted_until and listing.boosted_until > now
            else now
        )
        listing.boosted_until = base + timedelta(days=order.duration_days)
        listing.save(update_fields=["boosted_until", "updated_at"])

        order.status = ListingBoostOrder.Status.PAID
        order.razorpay_payment_id = data["razorpay_payment_id"]
        order.boosted_until = listing.boosted_until
        order.raw_response = {
            **(order.raw_response or {}),
            "payment": payment,
        }
        order.save(update_fields=[
            "status", "razorpay_payment_id", "boosted_until",
            "raw_response", "updated_at",
        ])

        ActivityLog.objects.create(
            type="listing-featured",
            message=(
                f"Listing boosted via {order.package} until "
                f"{listing.boosted_until:%Y-%m-%d}"
            ),
            target=str(listing.id),
        )
        return Response(self.get_serializer(listing).data)

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
