"""Authentication + user management views."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.adminpanel.permissions import IsAdminOperator
from .models import OtpCode  # noqa: F401  (re-exported for tests / shell)
from .serializers import (
    AdminNoteSerializer,
    BlockUserSerializer,
    GrantSubscriptionSerializer,
    OcbTokenObtainPairSerializer,
    OtpSendSerializer,
    OtpVerifySerializer,
    RegisterSerializer,
    UserRoleSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register  → create user + return JWT pair."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login → JWT pair + user."""
    serializer_class = OcbTokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)


class RefreshTokenView(TokenRefreshView):
    """POST /api/v1/auth/refresh → new access token."""
    permission_classes = (permissions.AllowAny,)


class MeView(generics.RetrieveUpdateAPIView):
    """GET / PATCH  /api/v1/auth/me  → current user."""
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class OtpSendView(generics.GenericAPIView):
    """POST /api/v1/auth/otp/send"""
    serializer_class = OtpSendSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        otp = ser.save()
        payload = {"sent": True}
        # In dev / console provider we surface the OTP for testing.
        from django.conf import settings as dj_settings
        if dj_settings.OTP_PROVIDER == "console" and dj_settings.DEBUG:
            payload["code"] = otp.code
        return Response(payload)


class OtpVerifyView(generics.GenericAPIView):
    """POST /api/v1/auth/otp/verify"""
    serializer_class = OtpVerifySerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"verified": True})


class UserAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only CRUD for users.

    Routes:
      GET    /api/v1/admin-panel/users/             list (search, filter by role/status)
      GET    /api/v1/admin-panel/users/<id>/        detail
      POST   /api/v1/admin-panel/users/<id>/block/  body: { blocked: bool }
      POST   /api/v1/admin-panel/users/<id>/note/   body: { note: str }
      GET    /api/v1/admin-panel/users/counts/      totals
    """
    serializer_class = UserSerializer
    permission_classes = (IsAdminOperator,)
    queryset = User.objects.all()
    filterset_fields = ("role", "status")
    search_fields = ("name", "email", "phone", "city")
    ordering_fields = ("date_joined", "last_login_at", "name")
    ordering = ("-date_joined",)

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(city__icontains=q)
            )
        return qs

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = self.get_object()
        ser = BlockUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user.status = (
            User.Status.BLOCKED if ser.validated_data["blocked"] else User.Status.ACTIVE
        )
        user.save(update_fields=["status", "updated_at"])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def note(self, request, pk=None):
        user = self.get_object()
        ser = AdminNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user.admin_note = ser.validated_data["note"]
        user.save(update_fields=["admin_note", "updated_at"])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def role(self, request, pk=None):
        """POST /api/v1/admin-panel/users/<id>/role/  body: { role: buyer|seller|both }"""
        from apps.adminpanel.models import ActivityLog

        user = self.get_object()
        ser = UserRoleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        old_role = user.role
        user.role = ser.validated_data["role"]
        user.save(update_fields=["role", "updated_at"])

        admin = getattr(request, "admin", None)
        ActivityLog.objects.create(
            actor_admin=admin,
            type="settings-updated",
            message=f"Changed role for {user.name} from {old_role} to {user.role}",
            target=str(user.id),
        )
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="grant-subscription")
    def grant_subscription(self, request, pk=None):
        """Activate a dealer trial / paid plan for a user (sales team flow)."""
        from apps.adminpanel.models import ActivityLog
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.plans import DEALER_TRIAL_PLANS, get_plan, is_dealer_trial_plan
        from apps.subscriptions.services import activate_subscription, get_active_subscription

        user = self.get_object()
        ser = GrantSubscriptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan_code = ser.validated_data["plan"]
        plan = get_plan(plan_code)
        if not plan or plan.code == "free":
            return Response(
                {"detail": "Unknown or invalid plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_dealer_trial_plan(plan.code):
            from apps.adminpanel.dealer_offers import merge_dealer_offer_campaign
            from apps.adminpanel.models import AppSettings

            campaign = merge_dealer_offer_campaign(AppSettings.singleton().dealer_offer)
            if not campaign.get("enabled"):
                return Response(
                    {"detail": "Dealer offer campaign is currently disabled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            max_grants = int(campaign.get("max_grants") or 0)
            if max_grants > 0:
                active_count = Subscription.objects.filter(
                    plan__in=DEALER_TRIAL_PLANS.keys(),
                    status=Subscription.Status.ACTIVE,
                    expires_at__gt=timezone.now(),
                ).count()
                existing = get_active_subscription(user)
                if not existing and active_count >= max_grants:
                    return Response(
                        {"detail": f"Dealer offer limit reached ({max_grants} slots)."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        admin = getattr(request, "admin", None)
        actor_name = admin.name if admin else "admin"
        sub = activate_subscription(
            user,
            plan,
            provider="admin",
            provider_payment_id="",
            notes=ser.validated_data.get("notes")
            or f"Granted by {actor_name} via admin panel",
        )

        # Promote to seller role so dealer can list cars.
        if user.role == User.Role.BUYER:
            user.role = User.Role.SELLER
            user.save(update_fields=["role", "updated_at"])

        ActivityLog.objects.create(
            actor_admin=admin,
            type="dealer-offer-granted" if is_dealer_trial_plan(plan.code) else "settings-updated",
            message=f"Granted {plan.name} to {user.name}",
            target=str(user.id),
            metadata={
                "plan": plan.code,
                "expires_at": sub.expires_at.isoformat(),
                "user_phone": user.phone,
            },
        )

        active = get_active_subscription(user)
        return Response({
            "subscription_id": str(sub.id),
            "plan": plan.code,
            "plan_name": plan.name,
            "expires_at": sub.expires_at,
            "user": UserSerializer(user).data,
            "active_subscription": {
                "plan": active.plan if active else plan.code,
                "expires_at": active.expires_at if active else sub.expires_at,
            },
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def counts(self, request):
        return Response({
            "total": User.objects.count(),
            "buyers": User.objects.filter(
                role__in=(User.Role.BUYER, User.Role.BOTH)
            ).count(),
            "sellers": User.objects.filter(
                role__in=(User.Role.SELLER, User.Role.BOTH)
            ).count(),
            "blocked": User.objects.filter(status=User.Status.BLOCKED).count(),
        })
