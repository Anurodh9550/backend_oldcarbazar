from rest_framework import permissions


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """Anyone can read. Only listing owner or admin can mutate."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if getattr(request, "admin", None) is not None:
            return True
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_staff:
            return True
        if obj.seller_id and obj.seller_id == u.id:
            return True
        # Older rows may have no seller FK — allow the registered phone owner.
        if not obj.seller_id and obj.seller_phone and getattr(u, "phone", ""):
            return obj.seller_phone == u.phone
        return False
