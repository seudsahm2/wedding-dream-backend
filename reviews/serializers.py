from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    userName = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "userName", "rating", "text", "createdAt"]

    def get_userName(self, obj: Review) -> str:
        if obj.user and getattr(obj.user, "username", None):
            return obj.user.username
        return obj.user_name or "Guest"


class ReviewCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=5000)

    def validate_name(self, value: str) -> str:
        return value.strip()

    def validate_text(self, value: str) -> str:
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Review text required")
        return v

    # Stubs to satisfy Serializer abstract methods
    def create(self, validated_data):  # pragma: no cover - handled in view
        return validated_data

    def update(self, instance, validated_data):  # pragma: no cover - not used
        return instance
