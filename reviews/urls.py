from django.urls import path
from .views import ListingReviewListCreateView

urlpatterns = [
    path("listings/<int:listing_id>/reviews/", ListingReviewListCreateView.as_view(), name="listing-reviews"),
]
