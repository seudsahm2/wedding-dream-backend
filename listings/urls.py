from django.urls import path
from .views import (
    CategoryListView,
    ListingListView,
    FeaturedListingListView,
    ListingDetailView,
    MyListingListView,
    PublishListingView,
    ImageUploadView,
    ListingAvailabilityCreateView,
    ListingAvailabilityMonthView,
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('listings/', ListingListView.as_view(), name='listing-list'),
    path('listings/featured/', FeaturedListingListView.as_view(), name='featured-listing-list'),
    path('listings/<int:pk>/', ListingDetailView.as_view(), name='listing-detail'),
    path('listings/mine/', MyListingListView.as_view(), name='my-listings'),
    path('listings/<int:pk>/publish/', PublishListingView.as_view(), name='listing-publish'),
    path('listings/<int:pk>/availability/', ListingAvailabilityCreateView.as_view(), name='listing-availability-create'),
    path('listings/<int:pk>/availability/month/', ListingAvailabilityMonthView.as_view(), name='listing-availability-month'),
    path('media/upload/', ImageUploadView.as_view(), name='image-upload'),
]
