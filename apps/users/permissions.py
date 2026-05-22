"""Custom permissions used across the API."""
from rest_framework import permissions


class IsSelfOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and (obj.id == request.user.id or request.user.is_staff)
        )


class IsSellerOrAdmin(permissions.BasePermission):
    """Allow access only to sellers/both or admin users."""

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u.is_authenticated
            and (u.is_staff or u.role in ("seller", "both"))
        )
