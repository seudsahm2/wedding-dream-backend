from django.urls import path
from .views import (
    MeView,
    PreferencesView,
    ProviderUpgradeView,
    RegisterProviderView,
    ProviderServiceTypeListView,
    CountriesListView,
    UsernameAvailabilityView,
    ProviderMetaView,
    UsernameReminderView,
)
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import ThrottledTokenObtainPairView, ThrottledRegisterView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/preferences", PreferencesView.as_view(), name="preferences"),
    path("me/upgrade-provider", ProviderUpgradeView.as_view(), name="upgrade-provider"),  # unified strict
    path("auth/register-provider", RegisterProviderView.as_view(), name="register-provider"),  # unified strict
    path("provider/types", ProviderServiceTypeListView.as_view(), name="provider-types"),
    path("countries", CountriesListView.as_view(), name="countries"),
    path("auth/username-available", UsernameAvailabilityView.as_view(), name="username-available"),
    path("auth/provider-meta", ProviderMetaView.as_view(), name="provider-meta"),
    path("auth/username-reminder", UsernameReminderView.as_view(), name="username-reminder"),
    # Convenience aliases for roadmap
    path("auth/register", ThrottledRegisterView.as_view(), name="register"),
    path("auth/login", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="refresh"),
]
