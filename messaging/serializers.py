from rest_framework import serializers
from .models import ContactRequest, MessageThread, Message, ThreadParticipant
from listings.models import Listing


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


class MessageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    thread_id = serializers.IntegerField(source="thread.id", read_only=True)
    sender = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "thread_id", "sender", "text", "createdAt"]

    def get_sender(self, obj) -> str:
        request = self.context.get("request")
        if request and request.user.is_authenticated and obj.sender_id == request.user.id:
            return "me"
        return "provider"


class MessageThreadListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    listingId = serializers.IntegerField(source="listing.id", read_only=True)
    title = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    lastUpdated = serializers.DateTimeField(source="last_updated", read_only=True)
    unreadCount = serializers.SerializerMethodField()

    class Meta:
        model = MessageThread
        fields = [
            "id",
            "listingId",
            "title",
            "avatar",
            "lastUpdated",
            "unreadCount",
        ]

    def get_title(self, obj) -> str:
        if getattr(obj, "listing", None):
            return obj.listing.title
        return "Conversation"

    def get_avatar(self, obj):
        if getattr(obj, "listing", None) and getattr(obj.listing, "image", None):
            img = obj.listing.image
            # If image is a path like "assets/foo.jpg", make it absolute for FE
            if isinstance(img, str) and not img.startswith("http"):
                return f"http://127.0.0.1:8000/{img.lstrip('/')}"
            return str(img)
        return None

    def get_unreadCount(self, obj) -> int:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return 0
        try:
            tp = ThreadParticipant.objects.get(thread=obj, user=user)
            return int(tp.unread_count)
        except ThreadParticipant.DoesNotExist:
            return 0


class MessageThreadDetailSerializer(MessageThreadListSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(MessageThreadListSerializer.Meta):
        fields = MessageThreadListSerializer.Meta.fields + ["messages"]

    def get_messages(self, obj):
        qs = self.context.get("messages_qs")
        if qs is None:
            qs = Message.objects.filter(thread=obj).order_by("created_at")
        return MessageSerializer(qs, many=True, context=self.context).data


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField()

    def validate_text(self, value: str) -> str:
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Message text required")
        if len(v) > 5000:
            raise serializers.ValidationError("Message too long")
        return v
