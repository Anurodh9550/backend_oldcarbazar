from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

from .models import ActivityLog, Admin, AppSettings

User = get_user_model()


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ("id", "name", "email", "role", "avatar_url", "last_login_at", "created_at")
        read_only_fields = fields


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        try:
            admin = Admin.objects.get(email=email)
        except Admin.DoesNotExist as exc:
            try:
                user = User.objects.get(email__iexact=email, is_staff=True)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password.") from exc
            auth_user = authenticate(
                request=self.context.get("request"),
                phone=user.phone,
                password=attrs["password"],
            )
            if not auth_user:
                raise serializers.ValidationError("Invalid email or password.") from exc
            attrs["staff_user"] = auth_user
            return attrs
        if not admin.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid email or password.")
        attrs["admin"] = admin
        return attrs


class AdminTokenResponseSerializer(serializers.Serializer):
    """Output shape returned by admin login."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    admin = AdminSerializer()


def admin_jwt_tokens(admin: Admin) -> dict:
    """Issue tokens that include an `is_admin` claim so middleware can tell apart."""
    refresh = RefreshToken()
    refresh["admin_id"] = str(admin.id)
    refresh["is_admin"] = True
    refresh["email"] = admin.email
    refresh["role"] = admin.role
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def staff_jwt_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_admin_name = serializers.CharField(source="actor_admin.name", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = (
            "id", "type", "message", "target", "metadata",
            "actor_admin", "actor_admin_name",
            "actor_user", "created_at",
        )
        read_only_fields = fields


class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = (
            "auto_approve_listings", "maintenance_mode",
            "email_notifications", "sms_notifications", "whatsapp_enabled",
            "max_photos_per_listing", "min_listing_price", "max_listing_price",
            "blocked_keywords", "support_email", "support_phone",
            "brand_color", "loan_tools_content", "dealer_offer", "ads", "updated_at",
        )
        read_only_fields = ("updated_at",)
