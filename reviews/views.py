from typing import Any, Dict, Type
from django.db.models import QuerySet
from rest_framework import generics, status, serializers as drf_serializers
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.shortcuts import get_object_or_404

from listings.models import Listing
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer


class GuestReviewThrottle(AnonRateThrottle):
    scope = "guest_reviews"


class ListingReviewListCreateView(generics.ListCreateAPIView):
    throttle_classes = [GuestReviewThrottle]
    serializer_class = ReviewSerializer
    queryset = Review.objects.all()

    def get_serializer_class(self) -> Type[drf_serializers.Serializer]:
        if self.request and self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_queryset(self) -> QuerySet[Review]:
        listing = get_object_or_404(Listing, pk=self.kwargs.get("listing_id"))
        return Review.objects.filter(listing=listing).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, pk=kwargs.get("listing_id"))
        ser = ReviewCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data: Dict[str, Any] = ser.validated_data  # type: ignore[assignment]
        review = Review.objects.create(
            listing=listing,
            user=request.user if request.user and request.user.is_authenticated else None,
            user_name=data.get("name", "").strip(),
            rating=data["rating"],
            text=data["text"],
        )
        out = ReviewSerializer(review)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

