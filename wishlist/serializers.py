from rest_framework import serializers
from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    listing_id = serializers.IntegerField(source="listing.id", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "listing_id", "listing_title", "added_at"]
