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
    text = serializers.CharField()
