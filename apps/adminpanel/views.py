"""Admin panel APIs: auth, dashboard, settings, activity, users."""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inquiries.models import Inquiry
from apps.listings.models import Listing
from apps.users.views import UserAdminViewSet  # noqa: F401  (re-exported in urls)

from .models import ActivityLog, Admin, AppSettings
from .permissions import IsAdminOperator
from .serializers import (
    ActivityLogSerializer,
    AdminLoginSerializer,
    AdminSerializer,
    AppSettingsSerializer,
    admin_jwt_tokens,
)

User = get_user_model()


class AdminLoginView(generics.GenericAPIView):
    """POST /api/v1/admin-panel/login → admin JWT pair."""
    serializer_class = AdminLoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        admin: Admin = ser.validated_data["admin"]
        admin.last_login_at = timezone.now()
        admin.save(update_fields=["last_login_at"])
        ActivityLog.objects.create(
            actor_admin=admin,
            type="admin-login",
            message=f"{admin.name} signed in",
            target=admin.email,
        )
        tokens = admin_jwt_tokens(admin)
        return Response({**tokens, "admin": AdminSerializer(admin).data})


class AdminMeView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/me → currently signed-in admin."""
    permission_classes = (IsAdminOperator,)
    serializer_class = AdminSerializer

    def get(self, request):
        admin = getattr(request, "admin", None)
        # Django superuser shortcut (no separate Admin row required).
        if not admin and request.user.is_authenticated and request.user.is_staff:
            return Response({
                "id": str(request.user.id),
                "name": request.user.name,
                "email": request.user.email,
                "role": "super-admin",
                "avatar_url": "",
                "last_login_at": request.user.last_login_at,
                "created_at": request.user.date_joined,
            })
        return Response(AdminSerializer(admin).data)


class DashboardStatsView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/dashboard"""
    permission_classes = (IsAdminOperator,)

    def get(self, request):
        from apps.listings.serializers import ListingSerializer  # local import to avoid cycles

        listings_qs = Listing.objects.all()
        inquiries_qs = Inquiry.objects.all()

        totals = {
            "listings": {
                "total": listings_qs.count(),
                "pending": listings_qs.filter(moderation="pending").count(),
                "featured": listings_qs.filter(featured=True).count(),
                "rejected": listings_qs.filter(moderation="rejected").count(),
            },
            "inquiries": {
                "total": inquiries_qs.count(),
                "new": inquiries_qs.filter(status="new").count(),
            },
            "users": {
                "total": User.objects.count(),
                "buyers": User.objects.filter(role__in=("buyer", "both")).count(),
                "sellers": User.objects.filter(role__in=("seller", "both")).count(),
                "blocked": User.objects.filter(status="blocked").count(),
            },
        }

        by_brand = list(
            listings_qs.values("brand")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        by_fuel = list(
            listings_qs.values("fuel").annotate(count=Count("id")).order_by("-count")
        )
        by_city = list(
            listings_qs.values("location").annotate(count=Count("id")).order_by("-count")[:10]
        )

        recent_listings = Listing.objects.order_by("-created_at")[:5]
        recent_activity = ActivityLog.objects.order_by("-created_at")[:10]

        return Response({
            "totals": totals,
            "breakdown": {
                "byBrand": by_brand,
                "byFuel": by_fuel,
                "byCity": by_city,
            },
            "recentListings": ListingSerializer(recent_listings, many=True).data,
            "recentActivity": ActivityLogSerializer(recent_activity, many=True).data,
        })


class AppSettingsView(generics.RetrieveUpdateAPIView):
    """GET / PATCH  /api/v1/admin-panel/settings"""
    serializer_class = AppSettingsSerializer
    permission_classes = (IsAdminOperator,)

    def get_object(self):
        return AppSettings.singleton()

    def perform_update(self, serializer):
        serializer.save()
        ActivityLog.objects.create(
            actor_admin=getattr(self.request, "admin", None),
            type="settings-updated",
            message="Platform settings updated",
        )


class ActivityLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """GET /api/v1/admin-panel/activity/"""
    queryset = ActivityLog.objects.select_related("actor_admin").all()
    serializer_class = ActivityLogSerializer
    permission_classes = (IsAdminOperator,)
    filterset_fields = ("type",)
    ordering = ("-created_at",)
