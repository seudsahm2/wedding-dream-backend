from django.urls import path
from .views import (
    MeView,
    PreferencesView,
    ProviderUpgradeView,
    RegisterProviderView,
    CountriesListView,
    UsernameAvailabilityView,
    EmailAvailabilityView,
    ProviderMetaView,
    UsernameReminderView,
    BusinessEmailVerifyView,
)
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import ThrottledTokenObtainPairView, ThrottledRegisterView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/preferences", PreferencesView.as_view(), name="preferences"),
    path("me/upgrade-provider", ProviderUpgradeView.as_view(), name="upgrade-provider"),  # unified strict
    path("auth/register-provider", RegisterProviderView.as_view(), name="register-provider"),  # unified strict
    path("countries", CountriesListView.as_view(), name="countries"),
    path("auth/username-available", UsernameAvailabilityView.as_view(), name="username-available"),
    path("auth/email-available", EmailAvailabilityView.as_view(), name="email-available"),
    path("auth/provider-meta", ProviderMetaView.as_view(), name="provider-meta"),
    path("auth/username-reminder", UsernameReminderView.as_view(), name="username-reminder"),
    path("auth/verify-business-email/<str:uid>/<str:token>", BusinessEmailVerifyView.as_view(), name="verify-business-email"),
    # Convenience aliases for roadmap
    path("auth/register", ThrottledRegisterView.as_view(), name="register"),
    path("auth/login", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="refresh"),
]
