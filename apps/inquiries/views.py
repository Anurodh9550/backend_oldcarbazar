from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.adminpanel.permissions import IsAdminOperator
from .models import Inquiry
from .serializers import (
    CreateInquirySerializer,
    InquirySerializer,
    InquiryStatusSerializer,
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
