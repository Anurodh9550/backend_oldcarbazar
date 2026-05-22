"""Authentication + user management views."""
from django.contrib.auth import get_user_model
from django.db.models import Q
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
    OcbTokenObtainPairSerializer,
    OtpSendSerializer,
    OtpVerifySerializer,
    RegisterSerializer,
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
