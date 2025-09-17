from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from listings.models import Listing
from .models import WishlistItem
from .serializers import WishlistItemSerializer


class WishlistListCreateView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		items = WishlistItem.objects.filter(user=request.user).select_related("listing").order_by("-added_at")
		return Response(WishlistItemSerializer(items, many=True).data)

	def post(self, request):
		listing_id = request.data.get("listing_id")
		if not listing_id:
			return Response({"detail": "listing_id is required"}, status=status.HTTP_400_BAD_REQUEST)
		listing = get_object_or_404(Listing, pk=listing_id)
		item, _created = WishlistItem.objects.get_or_create(user=request.user, listing=listing)
		return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)


class WishlistDeleteView(generics.DestroyAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def delete(self, request, listing_id: int):
		item = WishlistItem.objects.filter(user=request.user, listing_id=listing_id).first()
		if not item:
			return Response(status=status.HTTP_204_NO_CONTENT)
		item.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)

