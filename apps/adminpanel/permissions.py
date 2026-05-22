"""Permission classes for the admin panel."""
from rest_framework import permissions


class IsAdminOperator(permissions.BasePermission):
    """Pass if Django staff user OR admin JWT (set on request by auth class)."""

    message = "Admin access required."

    def has_permission(self, request, view) -> bool:
        u = getattr(request, "user", None)
        if u and getattr(u, "is_authenticated", False) and u.is_staff:
            return True
        return getattr(request, "admin", None) is not None
