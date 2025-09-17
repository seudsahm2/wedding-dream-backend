from rest_framework import serializers
from .models import ContactRequest


class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ["id", "listing", "name", "email_or_phone", "message", "created_at"]
        read_only_fields = ["id", "created_at"]


class ContactRequestCreateSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    name = serializers.CharField(max_length=120)
    email_or_phone = serializers.CharField(max_length=255)
    message = serializers.CharField()

    def create(self, validated_data):
        from listings.models import Listing

        listing_id = validated_data.pop("listing_id")
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            raise serializers.ValidationError({"listing_id": "Listing not found"})
        return ContactRequest.objects.create(listing=listing, **validated_data)
