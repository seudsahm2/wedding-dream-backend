from rest_framework import permissions


class IsProviderOrReadOnly(permissions.BasePermission):
    """Allow read-only for everyone; write only for authenticated provider role."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Import inside to avoid circular import at module load
        from users.models import UserProfile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return False
        return profile.role == UserProfile.ROLE_PROVIDER