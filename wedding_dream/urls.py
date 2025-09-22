"""
URL configuration for wedding_dream project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from users.views import ActivationRedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Browser activation convenience (GET). Djoser still expects POST to /api/v1/auth/users/activation/ for API usage.
    path("activate/<uid>/<token>", ActivationRedirectView.as_view(), name="activate"),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("listings.urls")),
    path("api/v1/", include("reviews.urls")),
    path("api/v1/", include("messaging.urls")),
    # Auth (Djoser + JWT)
    path("api/v1/auth/", include("djoser.urls")),
    path("api/v1/auth/", include("djoser.urls.jwt")),
    # Profile & Wishlist endpoints
    path("api/v1/", include("users.urls")),
    path("api/v1/", include("wishlist.urls")),
]

# Serve media and backend demo assets in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve backend/assets at /assets/
    from django.views.static import serve as static_serve  # type: ignore
    from django.urls import re_path
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", static_serve, {"document_root": settings.BACKEND_ASSETS_DIR}),
    ]
