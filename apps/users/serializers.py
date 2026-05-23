"""Serializers for the users app."""
from datetime import timedelta
from random import randint

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OtpCode, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "name", "email", "phone", "city", "avatar_url",
            "role", "status", "email_verified", "phone_verified",
            "admin_note", "login_count", "last_login_at",
            "date_joined", "updated_at",
        )
        read_only_fields = (
            "id", "role", "status", "email_verified", "phone_verified",
            "admin_note", "login_count", "last_login_at",
            "date_joined", "updated_at",
        )


class RegisterSerializer(serializers.ModelSerializer):
    """Register a buyer/seller. Phone is the primary identifier; email optional."""
    password = serializers.CharField(write_only=True, min_length=6, max_length=128)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, max_length=80)

    class Meta:
        model = User
        fields = ("name", "email", "phone", "password", "city")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already registered.")
        return value

    def validate_email(self, value):
        if not value:
            return None
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated):
        password = validated.pop("password")
        # Treat empty email as NULL so the unique-email index doesn't clash on "".
        if not validated.get("email"):
            validated["email"] = None
        user = User(**validated)
        user.set_password(password)
        user.login_count = 1
        user.last_login_at = timezone.now()
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Phone-first login. Email is also accepted for users who set one."""
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        ident = attrs["identifier"].strip()
        password = attrs["password"]
        if "@" in ident:
            lookup = {"email__iexact": ident}
        else:
            # Strip +91 / spaces / dashes, keep last 10 digits.
            digits = "".join(ch for ch in ident if ch.isdigit())
            lookup = {"phone": digits[-10:] if len(digits) >= 10 else digits}
        try:
            user = User.objects.get(**lookup)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found. Please register.")

        if user.is_blocked:
            raise serializers.ValidationError("Account blocked. Contact support.")

        auth_user = authenticate(
            request=self.context.get("request"),
            phone=user.phone, password=password,
        )
        if not auth_user:
            raise serializers.ValidationError("Invalid credentials.")

        attrs["user"] = auth_user
        return attrs


class OcbTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that uses our `identifier + password` shape."""
    username_field = "identifier"

    def validate(self, attrs):
        login = LoginSerializer(data=attrs, context=self.context)
        login.is_valid(raise_exception=True)
        user = login.validated_data["user"]

        user.login_count += 1
        user.last_login_at = timezone.now()
        user.save(update_fields=["login_count", "last_login_at", "updated_at"])

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class OtpSendSerializer(serializers.Serializer):
    target = serializers.CharField()
    purpose = serializers.ChoiceField(choices=OtpCode.Purpose.choices)

    def create(self, validated):
        code = f"{randint(100000, 999999)}"
        otp = OtpCode.objects.create(
            target=validated["target"],
            purpose=validated["purpose"],
            code=code,
            expires_at=timezone.now() + timedelta(
                seconds=settings.OTP_EXPIRY_SECONDS
            ),
        )
        return otp


class OtpVerifySerializer(serializers.Serializer):
    target = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=8)
    purpose = serializers.ChoiceField(choices=OtpCode.Purpose.choices)

    def validate(self, attrs):
        otp = (
            OtpCode.objects
            .filter(
                target=attrs["target"],
                code=attrs["code"],
                purpose=attrs["purpose"],
                consumed_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not otp:
            raise serializers.ValidationError("OTP not found.")
        if otp.is_expired:
            raise serializers.ValidationError("OTP expired.")
        attrs["otp"] = otp
        return attrs

    def save(self, **kwargs):
        otp = self.validated_data["otp"]
        otp.consumed_at = timezone.now()
        otp.save(update_fields=["consumed_at"])
        return otp


class AdminNoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000, allow_blank=True)


class BlockUserSerializer(serializers.Serializer):
    blocked = serializers.BooleanField()
