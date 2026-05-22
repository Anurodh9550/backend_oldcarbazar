"""Custom JWT authentication that supports both end-user and admin tokens.

End-user tokens carry the default ``user_id`` claim → loaded as a User instance.
Admin tokens carry ``is_admin: True`` + ``admin_id`` → returned as AnonymousUser
plus the admin instance stashed on ``request.admin``.

Permission classes (e.g. ``IsAdminOperator``) read ``request.admin``.
"""
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Admin


class OcbJWTAuthentication(JWTAuthentication):
    """Accepts either a user JWT or an admin JWT."""

    def get_user(self, validated_token):
        if validated_token.payload.get("is_admin"):
            admin_id = validated_token.payload.get("admin_id")
            try:
                admin = Admin.objects.get(pk=admin_id)
            except Admin.DoesNotExist:
                return AnonymousUser()
            user = AnonymousUser()
            user.admin = admin  # type: ignore[attr-defined]
            return user
        return super().get_user(validated_token)

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        # Surface admin on request for permission classes / views.
        admin = getattr(user, "admin", None)
        if admin is not None:
            request.admin = admin
        return result
