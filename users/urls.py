from django.urls import path
from .views import MeView, PreferencesView
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import ThrottledTokenObtainPairView, ThrottledRegisterView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/preferences", PreferencesView.as_view(), name="preferences"),
    # Convenience aliases for roadmap
    path("auth/register", ThrottledRegisterView.as_view(), name="register"),
    path("auth/login", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="refresh"),
]
