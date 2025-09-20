from rest_framework import permissions


class IsProviderOrReadOnly(permissions.BasePermission):
    """Allow read-only for everyone; write only for authenticated provider role."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from users.models import UserProfile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return False
        return profile.role == UserProfile.ROLE_PROVIDER


class IsProviderOwnerOrReadOnly(permissions.BasePermission):
    """Read: everyone can see published listings; drafts only visible to owner.
    Write: only provider owner can modify.
    """

    def has_permission(self, request, view):
        # For unsafe methods must be provider (reuse logic)
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from users.models import UserProfile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return False
        return profile.role == UserProfile.ROLE_PROVIDER

    def has_object_permission(self, request, view, obj):
        # SAFE: only allow if published, or owner viewing their own draft
        if request.method in permissions.SAFE_METHODS:
            if obj.status == 'published':
                return True
            if request.user.is_authenticated and obj.created_by_id == request.user.id:
                return True
            return False
        # UNSAFE: must be owner
        return request.user.is_authenticated and obj.created_by_id == request.user.id