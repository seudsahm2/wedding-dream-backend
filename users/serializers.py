from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, ProviderServiceType


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["language", "notifications", "role", "business_name", "business_phone", "business_type", "country", "city"]
        read_only_fields = ["role"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class ProviderUpgradeSerializer(serializers.Serializer):
    # Placeholder if we later need additional verification data
    confirm = serializers.BooleanField(default=True)


class ProviderServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderServiceType
        fields = ["slug", "name", "active"]
