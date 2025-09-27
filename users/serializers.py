from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import UserProfile, ProviderServiceType
from django.core.exceptions import ValidationError as DjangoValidationError
import phonenumbers


class UnifiedUserCreateSerializer(serializers.Serializer):
    """Single entry serializer for both normal and provider user creation.

    Optional provider fields: business_name, business_phone, business_type, country, city.
    If any provider field is supplied OR `is_provider` True, validation enforces all provider requirements.
    Always enforces password confirmation via password2.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True)
    # Provider specific (optional unless provider flow)
    business_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    business_phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    business_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_provider = serializers.BooleanField(required=False, default=False)
    recaptcha_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_username(self, v: str):
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError('Username already exists.')
        return v

    def validate_email(self, v: str):
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return v

    def _validate_provider_phone(self, raw: str, country: str):
        try:
            parsed = phonenumbers.parse(raw.strip(), country or None)
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError('Invalid phone number')
            region = phonenumbers.region_code_for_number(parsed)
            if region and country and region.upper() != country.upper():
                raise serializers.ValidationError('Phone country code mismatch')
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError('Could not parse phone number')

    def validate(self, attrs):
        # reCAPTCHA (optional) check before deeper validation to short-circuit bots
        from django.conf import settings
        if getattr(settings, 'RECAPTCHA_ENABLED', False):
            from core.recaptcha import verify_recaptcha
            token = attrs.get('recaptcha_token') or ''
            if not token:
                raise serializers.ValidationError({'recaptcha_token': ['Missing reCAPTCHA token']})
            ok, reason, score = verify_recaptcha(token, None)
            if not ok:
                raise serializers.ValidationError({'recaptcha_token': [f'Failed ({reason})']})
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({'password2': ['Passwords do not match']})
        provider_flag = attrs.get('is_provider') or any(attrs.get(f) for f in ['business_name', 'business_phone', 'business_type', 'country', 'city'])
        attrs['provider_flag'] = bool(provider_flag)
        if provider_flag:
            # Enforce required provider fields
            missing = [f for f in ['business_name', 'business_phone', 'business_type', 'country', 'city'] if not str(attrs.get(f) or '').strip()]
            if missing:
                raise serializers.ValidationError({f: ['This field is required for provider accounts.'] for f in missing})
            country = (attrs.get('country') or '').upper()
            if len(country) != 2:
                raise serializers.ValidationError({'country': ['Must be 2-letter ISO code']})
            # Validate provider type existence if table populated
            btype = attrs.get('business_type')
            if btype and not ProviderServiceType.objects.filter(slug=btype, active=True).exists():
                raise serializers.ValidationError({'business_type': ['Invalid provider type']})
            # Phone validation
            phone_raw = attrs.get('business_phone') or ''
            normalized_phone = self._validate_provider_phone(phone_raw, country)
            attrs['business_phone'] = normalized_phone
            attrs['country'] = country
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        provider_flag = validated_data.pop('provider_flag', False)
        validated_data.pop('password2', None)
        provider_fields = {k: validated_data.pop(k, None) for k in ['business_name', 'business_phone', 'business_type', 'country', 'city', 'is_provider']}
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        # Force inactive for activation flow
        if user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if provider_flag:
            profile.role = UserProfile.ROLE_PROVIDER
            profile.business_name = provider_fields.get('business_name')
            profile.business_phone = provider_fields.get('business_phone')
            profile.business_type = provider_fields.get('business_type')
            profile.country = provider_fields.get('country')
            profile.city = provider_fields.get('city')
        profile.email_verified = False
        profile.save()
        return user

    def to_representation(self, instance: User):
        profile = getattr(instance, 'profile', None)
        base = {
            'id': instance.id,
            'username': instance.username,
            'email': instance.email,
        }
        if profile:
            base.update({
                'role': profile.role,
                'is_provider': profile.role == UserProfile.ROLE_PROVIDER,
                'country': profile.country,
                'business_phone': profile.business_phone,
                'email_verified': profile.email_verified,
            })
        base['activation_required'] = True
        return base


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
