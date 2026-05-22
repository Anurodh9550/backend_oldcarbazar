from rest_framework import permissions


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """Anyone can read. Only listing owner or admin can mutate."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        u = request.user
        return bool(
            u.is_authenticated
            and (u.is_staff or (obj.seller_id and obj.seller_id == u.id))
        )
