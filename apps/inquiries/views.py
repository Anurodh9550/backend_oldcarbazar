from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.adminpanel.permissions import IsAdminOperator
from .models import Inquiry, Offer, TestDriveBooking
from .serializers import (
    CreateInquirySerializer,
    CreateOfferSerializer,
    CreateTestDriveSerializer,
    InquirySerializer,
    InquiryStatusSerializer,
    OfferResponseSerializer,
    OfferSerializer,
    TestDriveBookingSerializer,
    TestDriveStatusSerializer,
)


class InquiryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Inquiries API.

    - POST /api/v1/inquiries/             public (anyone can ask about a listing)
    - GET  /api/v1/inquiries/             admin-only list
    - GET  /api/v1/inquiries/<id>/        admin-only detail
    - POST /api/v1/inquiries/<id>/status/ admin-only status update
    - GET  /api/v1/inquiries/mine/        buyer/seller's own inquiries
    """
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    filterset_fields = ("status", "channel", "city")
    search_fields = ("buyer_name", "buyer_phone", "listing_title", "message")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action == "mine":
            return [permissions.IsAuthenticated()]
        return [IsAdminOperator()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateInquirySerializer
        return InquirySerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inquiry = ser.save()
        return Response(
            InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = Inquiry.objects.filter(
            buyer=request.user
        ) | Inquiry.objects.filter(seller=request.user)
        qs = qs.distinct().order_by("-created_at")
        page = self.paginate_queryset(qs)
        ser = InquirySerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        inquiry = self.get_object()
        ser = InquiryStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inquiry.status = ser.validated_data["status"]
        inquiry.save(update_fields=["status", "updated_at"])
        return Response(InquirySerializer(inquiry).data)


class TestDriveBookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Test drive bookings.

    - POST /api/v1/test-drives/             public create
    - GET  /api/v1/test-drives/             admin-only list
    - GET  /api/v1/test-drives/mine/        buyer + seller's own bookings
    - POST /api/v1/test-drives/<id>/status/ buyer (cancel) or seller (confirm/cancel/complete)
    """
    queryset = TestDriveBooking.objects.select_related("listing").all()
    filterset_fields = ("status",)
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in ("mine", "set_status"):
            return [permissions.IsAuthenticated()]
        return [IsAdminOperator()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateTestDriveSerializer
        return TestDriveBookingSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        booking = ser.save()
        return Response(
            TestDriveBookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = TestDriveBooking.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ).distinct().order_by("-created_at")
        page = self.paginate_queryset(qs)
        ser = TestDriveBookingSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        booking = self.get_object()
        # Authorisation: buyer can cancel their own; seller can change status
        # of bookings on their listings; admin can do anything.
        is_buyer = booking.buyer_id == request.user.id
        is_seller = booking.seller_id == request.user.id
        if not (is_buyer or is_seller or request.user.is_staff):
            return Response({"detail": "Not allowed."}, status=403)

        ser = TestDriveStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_status = ser.validated_data["status"]

        if is_buyer and not (is_seller or request.user.is_staff):
            # Buyer may only cancel.
            if new_status != TestDriveBooking.Status.CANCELLED:
                return Response(
                    {"detail": "Buyers can only cancel a booking."}, status=403
                )

        booking.status = new_status
        if ser.validated_data.get("seller_response"):
            booking.seller_response = ser.validated_data["seller_response"]
        booking.save(update_fields=["status", "seller_response", "updated_at"])
        return Response(TestDriveBookingSerializer(booking).data)


class OfferViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Price offers from buyers to sellers.

    - POST /api/v1/offers/                 public create
    - GET  /api/v1/offers/                 admin-only list
    - GET  /api/v1/offers/mine/            buyer + seller's own offers
    - POST /api/v1/offers/<id>/respond/    seller accepts / rejects / counters
    - POST /api/v1/offers/<id>/withdraw/   buyer withdraws their own offer
    """
    queryset = Offer.objects.select_related("listing").all()
    filterset_fields = ("status",)
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in ("mine", "respond", "withdraw"):
            return [permissions.IsAuthenticated()]
        return [IsAdminOperator()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOfferSerializer
        return OfferSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = ser.save()
        return Response(
            OfferSerializer(offer).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = Offer.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ).distinct().order_by("-created_at")
        page = self.paginate_queryset(qs)
        ser = OfferSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        offer = self.get_object()
        is_seller = offer.seller_id == request.user.id
        if not (is_seller or request.user.is_staff):
            return Response(
                {"detail": "Only the listing's seller can respond."}, status=403
            )
        ser = OfferResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer.status = ser.validated_data["status"]
        if ser.validated_data.get("counter_amount") is not None:
            offer.counter_amount = ser.validated_data["counter_amount"]
        if ser.validated_data.get("seller_response"):
            offer.seller_response = ser.validated_data["seller_response"]
        offer.save(
            update_fields=[
                "status", "counter_amount", "seller_response", "updated_at",
            ]
        )
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        if offer.buyer_id != request.user.id:
            return Response(
                {"detail": "Only the buyer can withdraw their offer."},
                status=403,
            )
        offer.status = Offer.Status.WITHDRAWN
        offer.save(update_fields=["status", "updated_at"])
        return Response(OfferSerializer(offer).data)
