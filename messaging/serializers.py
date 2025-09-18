from rest_framework import serializers
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from .models import ContactRequest, MessageThread, Message
from django.apps import apps


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
        listing_id = validated_data.pop("listing_id")
        try:
            ListingModel = apps.get_model('listings', 'Listing')
            listing = ListingModel.objects.get(pk=listing_id)
        except ObjectDoesNotExist as exc:
            raise serializers.ValidationError({"listing_id": "Listing not found"}) from exc
        ContactRequestModel = apps.get_model('messaging', 'ContactRequest')
        return ContactRequestModel.objects.create(listing=listing, **validated_data)

    def update(self, instance, validated_data):  # pragma: no cover - not used
        raise NotImplementedError("Update not supported for ContactRequestCreateSerializer")


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
        if not getattr(obj, "listing", None) or not getattr(obj.listing, "image", None):
            return None
        img = str(obj.listing.image).strip()
        # Already absolute
        if img.startswith("http://") or img.startswith("https://"):
            return img
        request = self.context.get("request")
        # Backend assets
        if img.startswith("assets/") or img.startswith("/assets/"):
            path = img.lstrip('/')
            abs_url = f"{settings.BACKEND_ASSETS_URL}{path.split('assets/', 1)[-1]}"
            return request.build_absolute_uri(abs_url) if request else abs_url
        # Relative media path
        media_path = img.lstrip('/')
        abs_url = f"{settings.MEDIA_URL}{media_path}"
        return request.build_absolute_uri(abs_url) if request else abs_url

    def get_unreadCount(self, obj) -> int:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return 0
        try:
            ThreadParticipantModel = apps.get_model('messaging', 'ThreadParticipant')
            tp = ThreadParticipantModel.objects.get(thread=obj, user=user)
            return int(getattr(tp, 'unread_count', 0))
        except ObjectDoesNotExist:
            return 0


class MessageThreadDetailSerializer(MessageThreadListSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(MessageThreadListSerializer.Meta):
        fields = MessageThreadListSerializer.Meta.fields + ["messages"]

    def get_messages(self, obj):
        qs = self.context.get("messages_qs")
        if qs is None:
            MessageModel = apps.get_model('messaging', 'Message')
            qs = MessageModel.objects.filter(thread=obj).order_by("created_at")
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

    def create(self, validated_data):  # pragma: no cover - not used by DRF directly
        return validated_data

    def update(self, instance, validated_data):  # pragma: no cover - not used
        raise NotImplementedError("Update not supported for MessageCreateSerializer")
