from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.adminpanel.permissions import IsAdminOperator
from .models import Inquiry, ListingView, LoanInquiry, Offer, TestDriveBooking
from .serializers import (
    CreateInquirySerializer,
    CreateLoanInquirySerializer,
    CreateOfferSerializer,
    CreateTestDriveSerializer,
    InquirySerializer,
    InquiryStatusSerializer,
    LoanInquirySerializer,
    LoanInquiryStatusSerializer,
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
        from apps.users.seller_score import mark_inquiry_responded

        inquiry = self.get_object()
        ser = InquiryStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inquiry.status = ser.validated_data["status"]
        if inquiry.status == Inquiry.Status.RESPONDED:
            mark_inquiry_responded(inquiry)
        else:
            inquiry.save(update_fields=["status", "updated_at"])
        return Response(InquirySerializer(inquiry).data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="mark-responded",
    )
    def mark_responded(self, request, pk=None):
        from apps.users.seller_score import mark_inquiry_responded

        inquiry = Inquiry.objects.filter(id=pk, seller=request.user).first()
        if not inquiry:
            return Response(
                {"detail": "Inquiry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        mark_inquiry_responded(inquiry)
        return Response(InquirySerializer(inquiry).data)


def _iso(dt):
    return dt.isoformat() if dt else None


class SellerLeadsView(APIView):
    """Unified leads feed for the logged-in seller/dealer.

    Combines every signal of buyer interest on the seller's own listings:
    view-leads (who looked), inquiries, price offers and test-drive requests.
    Returns:
      - `summary`     : headline counts
      - `per_listing` : interest broken down by product (which car)
      - `leads`       : a single recent, sorted feed of all lead events
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user

        views = list(
            ListingView.objects.filter(seller=user).order_by("-updated_at")[:200]
        )
        inquiries = list(
            Inquiry.objects.filter(seller=user).order_by("-created_at")[:200]
        )
        offers = list(
            Offer.objects.filter(seller=user).order_by("-created_at")[:200]
        )
        test_drives = list(
            TestDriveBooking.objects.filter(seller=user).order_by("-created_at")[:200]
        )

        leads: list[dict] = []

        for v in views:
            leads.append({
                "id": str(v.id),
                "type": "view",
                "listing_id": str(v.listing_id) if v.listing_id else "",
                "listing_title": v.listing_title,
                "listing_price": v.listing_price,
                "name": v.viewer_name or "Guest viewer",
                "phone": v.viewer_phone or "",
                "email": v.viewer_email or "",
                "message": (
                    f"Viewed this car {v.view_count} time(s)"
                    if v.view_count > 1
                    else "Viewed this car"
                ),
                "amount": None,
                "status": "new",
                "city": v.city or "",
                "created_at": _iso(v.updated_at),
            })

        for i in inquiries:
            leads.append({
                "id": str(i.id),
                "type": i.channel if i.channel in ("whatsapp", "call") else "inquiry",
                "listing_id": str(i.listing_id) if i.listing_id else "",
                "listing_title": i.listing_title,
                "listing_price": i.listing_price,
                "name": i.buyer_name,
                "phone": i.buyer_phone,
                "email": i.buyer_email or "",
                "message": i.message,
                "amount": None,
                "status": i.status,
                "city": i.city or "",
                "created_at": _iso(i.created_at),
            })

        for o in offers:
            leads.append({
                "id": str(o.id),
                "type": "offer",
                "listing_id": str(o.listing_id) if o.listing_id else "",
                "listing_title": o.listing_title,
                "listing_price": "",
                "name": o.buyer_name,
                "phone": o.buyer_phone,
                "email": o.buyer_email or "",
                "message": o.message or "Made a price offer",
                "amount": float(o.amount) if o.amount is not None else None,
                "status": o.status,
                "city": "",
                "created_at": _iso(o.created_at),
            })

        for t in test_drives:
            leads.append({
                "id": str(t.id),
                "type": "test_drive",
                "listing_id": str(t.listing_id) if t.listing_id else "",
                "listing_title": t.listing_title,
                "listing_price": "",
                "name": t.buyer_name,
                "phone": t.buyer_phone,
                "email": t.buyer_email or "",
                "message": t.message or f"Test drive request for {_iso(t.scheduled_at)}",
                "amount": None,
                "status": t.status,
                "city": "",
                "created_at": _iso(t.created_at),
            })

        leads.sort(key=lambda x: x["created_at"] or "", reverse=True)

        # Per-listing breakdown: which product is getting interest.
        per_listing: dict[str, dict] = {}
        for lead in leads:
            lid = lead["listing_id"]
            if not lid:
                continue
            row = per_listing.setdefault(lid, {
                "listing_id": lid,
                "listing_title": lead["listing_title"],
                "listing_price": lead["listing_price"],
                "views": 0,
                "inquiries": 0,
                "offers": 0,
                "test_drives": 0,
                "total": 0,
            })
            if lead["type"] == "view":
                row["views"] += 1
            elif lead["type"] == "offer":
                row["offers"] += 1
            elif lead["type"] == "test_drive":
                row["test_drives"] += 1
            else:
                row["inquiries"] += 1
            row["total"] += 1

        per_listing_list = sorted(
            per_listing.values(), key=lambda r: r["total"], reverse=True
        )

        summary = {
            "views": len(views),
            "inquiries": len(inquiries),
            "offers": len(offers),
            "test_drives": len(test_drives),
            "total": len(leads),
            "new_inquiries": sum(1 for i in inquiries if i.status == Inquiry.Status.NEW),
        }

        return Response({
            "summary": summary,
            "per_listing": per_listing_list,
            "leads": leads[:200],
        })


class LoanInquiryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Used-car loan applications.

    - POST /api/v1/loan-inquiries/             public (anyone can apply)
    - GET  /api/v1/loan-inquiries/             admin-only list
    - GET  /api/v1/loan-inquiries/<id>/        admin-only detail
    - POST /api/v1/loan-inquiries/<id>/status/ admin-only status update
    - DELETE /api/v1/loan-inquiries/<id>/      admin-only delete
    """

    queryset = LoanInquiry.objects.all()
    serializer_class = LoanInquirySerializer
    filterset_fields = ("status", "bank_name", "loan_partner", "employment_type", "city")
    search_fields = ("full_name", "mobile", "email", "city")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [IsAdminOperator()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateLoanInquirySerializer
        return LoanInquirySerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inquiry = ser.save()
        return Response(
            LoanInquirySerializer(inquiry).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        inquiry = self.get_object()
        ser = LoanInquiryStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inquiry.status = ser.validated_data["status"]
        inquiry.save(update_fields=["status", "updated_at"])
        return Response(LoanInquirySerializer(inquiry).data)


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
