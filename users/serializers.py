from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile
from listings.models import Category


class UserProfileSerializer(serializers.ModelSerializer):
    provider_categories = serializers.SerializerMethodField(read_only=True)
    provider_subchoices = serializers.JSONField(required=False)
    provider_subchoice_tokens = serializers.ListField(child=serializers.CharField(), read_only=True)
    class Meta:
        model = UserProfile
        fields = [
            "language",
            "notifications",
            "role",
            "business_name",
            "business_phone",
            "business_type",
            "business_email",
            "business_email_verified",
            "country",
            "city",
            "provider_categories",
            "provider_subchoices",
            "provider_subchoice_tokens",
        ]
        read_only_fields = ["role"]

    def get_provider_categories(self, obj):
        try:
            return [
                {"slug": c.slug, "name": c.name}
                for c in obj.provider_categories.all().order_by('name')
            ]
        except Exception:
            return []

    @staticmethod
    def _flatten_tokens(subchoices):
        tokens = []
        if isinstance(subchoices, dict):
            for group, items in subchoices.items():
                if not isinstance(items, (list, tuple)):
                    continue
                group_label = str(group).strip()
                for v in items:
                    val = str(v).strip()
                    if group_label and val:
                        tokens.append(f"{group_label}:{val}")
        # dedupe + stable order
        return sorted(set(tokens))

    def update(self, instance, validated_data):
        # Update base fields first
        instance = super().update(instance, validated_data)
        # If provider_subchoices provided, refresh tokens
        if 'provider_subchoices' in validated_data:
            instance.provider_subchoice_tokens = self._flatten_tokens(validated_data.get('provider_subchoices') or {})
            instance.save(update_fields=['provider_subchoice_tokens'])
        return instance


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class ProviderUpgradeSerializer(serializers.Serializer):
    # Placeholder if we later need additional verification data
    confirm = serializers.BooleanField(default=True)

