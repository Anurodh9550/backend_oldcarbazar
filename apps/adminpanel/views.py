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
    staff_jwt_tokens,
)

User = get_user_model()


class AdminLoginView(generics.GenericAPIView):
    """POST /api/v1/admin-panel/login → admin JWT pair."""
    serializer_class = AdminLoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        staff_user = ser.validated_data.get("staff_user")
        if staff_user is not None:
            staff_user.last_login_at = timezone.now()
            staff_user.save(update_fields=["last_login_at"])
            tokens = staff_jwt_tokens(staff_user)
            return Response({
                **tokens,
                "admin": {
                    "id": str(staff_user.id),
                    "name": staff_user.name,
                    "email": staff_user.email,
                    "role": "super-admin" if staff_user.is_superuser else "moderator",
                    "avatar_url": staff_user.avatar_url,
                    "last_login_at": staff_user.last_login_at,
                    "created_at": staff_user.date_joined,
                },
            })

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


class AdminPaymentsView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/payments/

    All money flowing through the platform, for the admin panel:
      • subscriptions — every Pro plan activation (with Razorpay txn ids)
      • boosts        — every paid listing boost (with Razorpay txn ids)
    """
    permission_classes = (IsAdminOperator,)

    def get(self, request):
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.plans import get_plan
        from apps.listings.models import ListingBoostOrder

        sub_rows = []
        subscriptions = (
            Subscription.objects
            .select_related("user", "razorpay_order")
            .order_by("-created_at")
        )
        for sub in subscriptions:
            plan = get_plan(sub.plan)
            rzp = getattr(sub, "razorpay_order", None)
            sub_rows.append({
                "id": str(sub.id),
                "user_name": sub.user.name if sub.user_id else "—",
                "user_phone": sub.user.phone if sub.user_id else "",
                "user_email": (sub.user.email or "") if sub.user_id else "",
                "plan": sub.plan,
                "plan_name": plan.name if plan else sub.plan,
                "amount_inr": sub.amount_inr,
                "status": sub.status,
                "provider": sub.provider,
                "razorpay_order_id": rzp.razorpay_order_id if rzp else "",
                "razorpay_payment_id": (
                    rzp.razorpay_payment_id if rzp else sub.provider_payment_id
                ),
                "receipt": rzp.receipt if rzp else f"ocb_sub_{sub.id.hex[:12]}",
                "invoice_number": (
                    f"OCB-{sub.started_at:%Y%m%d}-"
                    f"{str(sub.id).split('-')[0].upper()}"
                ),
                "started_at": sub.started_at,
                "expires_at": sub.expires_at,
                "created_at": sub.created_at,
            })

        boost_rows = []
        boosts = (
            ListingBoostOrder.objects
            .select_related("user", "listing")
            .order_by("-created_at")
        )
        for order in boosts:
            boost_rows.append({
                "id": str(order.id),
                "user_name": order.user.name if order.user_id else "—",
                "user_phone": order.user.phone if order.user_id else "",
                "user_email": (order.user.email or "") if order.user_id else "",
                "listing_id": str(order.listing_id) if order.listing_id else "",
                "listing_title": order.listing.title if order.listing_id else "—",
                "package": order.package,
                "duration_days": order.duration_days,
                "amount_inr": order.amount_inr,
                "status": order.status,
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": order.razorpay_payment_id,
                "receipt": order.receipt,
                "invoice_number": f"OCB-BOOST-{str(order.id).split('-')[0].upper()}",
                "boosted_until": order.boosted_until,
                "created_at": order.created_at,
            })

        sub_revenue = sum(r["amount_inr"] for r in sub_rows)
        boost_revenue = sum(
            r["amount_inr"] for r in boost_rows if r["status"] == "paid"
        )

        return Response({
            "subscriptions": sub_rows,
            "boosts": boost_rows,
            "summary": {
                "subscriptions_count": len(sub_rows),
                "subscriptions_revenue": sub_revenue,
                "boosts_count": len([r for r in boost_rows if r["status"] == "paid"]),
                "boosts_revenue": boost_revenue,
                "total_revenue": sub_revenue + boost_revenue,
            },
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


class LoanToolsContentView(generics.GenericAPIView):
    """GET /api/v1/loan-tools/content/ — public Loan & Tools copy for the storefront."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        settings_row = AppSettings.singleton()
        return Response({"content": settings_row.loan_tools_content})


class AdsView(generics.GenericAPIView):
    """GET /api/v1/ads/ — public ad banners for the website + mobile app.

    Only enabled ads are returned. Optional query params let a client narrow
    results without doing the filtering itself:
      • ?platform=web|app   → only ads targeting that platform (or "both")
      • ?page=home|all|...  → only ads whose target pages include this page
    """

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        ads = AppSettings.singleton().ads or []
        if not isinstance(ads, list):
            ads = []

        enabled = [ad for ad in ads if isinstance(ad, dict) and ad.get("enabled")]

        platform = request.query_params.get("platform")
        if platform:
            enabled = [
                ad for ad in enabled
                if (ad.get("platform") or "both") in (platform, "both")
            ]

        page = request.query_params.get("page")
        if page:
            enabled = [
                ad for ad in enabled
                if page in (ad.get("pages") or []) or "all" in (ad.get("pages") or [])
            ]

        return Response({"ads": enabled})


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
