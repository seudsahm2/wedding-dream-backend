from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class PerIPScopeThrottle(SimpleRateThrottle):
    scope = ""

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class PerUserScopeThrottle(UserRateThrottle):
    scope = ""


class AuthLoginThrottle(PerIPScopeThrottle):
    scope = "auth_login"


class AuthRegisterThrottle(PerIPScopeThrottle):
    scope = "auth_register"


class ContactRequestUserThrottle(PerUserScopeThrottle):
    scope = "contact_requests_user"


class WishlistModifyThrottle(PerUserScopeThrottle):
    scope = "wishlist_modify"


class PreferencesUpdateThrottle(PerUserScopeThrottle):
    scope = "preferences_update"


class UserReviewThrottle(PerUserScopeThrottle):
    scope = "user_reviews"


class MessageSendThrottle(PerUserScopeThrottle):
    scope = "messages_send"


class ThreadStartThrottle(PerUserScopeThrottle):
    scope = "threads_start"


class UsernameAvailabilityThrottle(PerIPScopeThrottle):
    """Throttle rapid anonymous username availability polling to protect DB."""
    scope = "username_available"


class UsernameReminderThrottle(PerIPScopeThrottle):
    """Throttle username reminder requests by IP to mitigate enumeration & abuse."""
    scope = "username_reminder"
