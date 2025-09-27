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


class AuthLoginUserThrottle(SimpleRateThrottle):
    """Throttle login attempts per supplied username/email independent of IP.

    Mitigates rapid brute force across rotating IPs and protects specific accounts.
    """
    scope = "auth_login_user"

    def get_cache_key(self, request, view):  # type: ignore[override]
        if not request.data:
            return None
        ident = str(request.data.get('username') or '').strip().lower()
        if not ident:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


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


class EmailChangeThrottle(PerUserScopeThrottle):
    """Throttle email change requests per authenticated user."""
    scope = "email_change"
