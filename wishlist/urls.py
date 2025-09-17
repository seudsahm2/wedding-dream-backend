from django.urls import path
from .views import WishlistListCreateView, WishlistDeleteView

urlpatterns = [
    path("wishlist", WishlistListCreateView.as_view(), name="wishlist"),
    path("wishlist/<int:listing_id>", WishlistDeleteView.as_view(), name="wishlist-delete"),
]
