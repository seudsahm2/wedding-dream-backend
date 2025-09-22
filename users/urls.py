from django.urls import path
from .views import (
    MeView,
    PreferencesView,
    ProviderUpgradeView,
    ProviderUpgradeV2View,
    RegisterProviderView,
    RegisterProviderV2View,
    ProviderServiceTypeListView,
    CountriesListView,
)
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import ThrottledTokenObtainPairView, ThrottledRegisterView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/preferences", PreferencesView.as_view(), name="preferences"),
    path("me/upgrade-provider", ProviderUpgradeView.as_view(), name="upgrade-provider"),
    path("me/upgrade-provider-v2", ProviderUpgradeV2View.as_view(), name="upgrade-provider-v2"),
    path("auth/register-provider", RegisterProviderView.as_view(), name="register-provider"),
    path("auth/register-provider-v2", RegisterProviderV2View.as_view(), name="register-provider-v2"),
    path("provider/types", ProviderServiceTypeListView.as_view(), name="provider-types"),
    path("countries", CountriesListView.as_view(), name="countries"),
    # Convenience aliases for roadmap
    path("auth/register", ThrottledRegisterView.as_view(), name="register"),
    path("auth/login", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="refresh"),
]
