from rest_framework import serializers
from django.conf import settings
from .models import Category, Listing, ListingAvailability
from django.db import IntegrityError, transaction

class CategorySerializer(serializers.ModelSerializer):
    key = serializers.CharField(source='slug')
    label = serializers.CharField(source='name')

    class Meta:
        model = Category
        fields = ['key', 'label']

class ListingSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.slug')
    # Make image writable so client can send uploaded URL; we'll still transform it on output
    image = serializers.CharField()
    status = serializers.CharField(read_only=True)
    published_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)
    provider_name = serializers.SerializerMethodField(read_only=True)
    provider_city = serializers.SerializerMethodField(read_only=True)
    provider_country = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id',
            'title',
            'category',
            'type_label',
            'image',
            'image_thumb',
            'rating',
            'review_count',
            'location',
            'capacity',
            'price_range',
            'price_min',
            'features',
            'badges',
            'featured',
            'venue_attrs',
            'attire_attrs',
            'catering_attrs',
            'rental_attrs',
            'service_attrs',
            'accessory_attrs',
            'status',
            'published_at',
            'created_by',
            'provider_name',
            'provider_city',
            'provider_country',
        ]

    def validate(self, attrs):
        # Enforce attire-bridal attribute schema basics according to roadmap
        category_obj = attrs.get('category') if isinstance(attrs.get('category'), Category) else None
        attire_attrs = attrs.get('attire_attrs') or {}
        if category_obj and category_obj.slug == 'attire-bridal':
            allowed_keys = { 'sizeRange', 'fabricTypes', 'customizationOptions', 'rental', 'images', 'deliveryAvailable' }
            extra = set(attire_attrs.keys()) - allowed_keys
            if extra:
                raise serializers.ValidationError({'attire_attrs': f'Unexpected keys: {sorted(extra)}'})
            # Required fields
            if 'sizeRange' not in attire_attrs or not str(attire_attrs.get('sizeRange')).strip():
                raise serializers.ValidationError({'attire_attrs': 'sizeRange required'})
            if 'fabricTypes' not in attire_attrs or not isinstance(attire_attrs.get('fabricTypes'), list) or not attire_attrs.get('fabricTypes'):
                raise serializers.ValidationError({'attire_attrs': 'fabricTypes must be non-empty array'})
            # Optional arrays
            if 'customizationOptions' in attire_attrs and not isinstance(attire_attrs['customizationOptions'], list):
                raise serializers.ValidationError({'attire_attrs': 'customizationOptions must be an array'})
            if 'images' in attire_attrs:
                imgs = attire_attrs['images']
                if not isinstance(imgs, list) or len(imgs) == 0:
                    raise serializers.ValidationError({'attire_attrs': 'images must be a non-empty array when provided'})
                # set primary listing.image from first if not explicitly passed
                if not attrs.get('image') and imgs:
                    attrs['image'] = imgs[0]
        return super().validate(attrs)

    def _represent_image(self, instance: Listing):
        url = (instance.image or '').strip()
        if not url:
            return '/src/assets/luxury-wedding-hall.jpg'
        # Pass through absolute or vite asset path
        if url.startswith(('http://', 'https://', '/src/assets/')):
            return url
        # If using Supabase and we stored a relative path (uploads/...) build public URL
        from django.conf import settings as dj_settings
        backend = getattr(dj_settings, 'MEDIA_STORAGE_BACKEND', 'local')
        supabase_url = getattr(dj_settings, 'SUPABASE_URL', '')
        bucket = getattr(dj_settings, 'SUPABASE_BUCKET', '')
        if backend in ('supabase', 'auto') and supabase_url and bucket and url.startswith('uploads/'):
            return f"{supabase_url}/storage/v1/object/public/{bucket}/{url}"
        request = self.context.get('request')
        # Backend assets path
        if url.startswith(('assets/', '/assets/')):
            path = url.lstrip('/')
            abs_url = f"{settings.BACKEND_ASSETS_URL}{path.split('assets/', 1)[-1]}"
            if request:
                return request.build_absolute_uri(abs_url)
            return abs_url
        # Treat as relative media path
        media_path = url.lstrip('/')
        abs_url = f"{settings.MEDIA_URL}{media_path}"
        if request:
            return request.build_absolute_uri(abs_url)
        return abs_url

    def create(self, validated_data):
        # validated_data['category'] will be {'slug': 'value'} because of source mapping
        category_data = validated_data.pop('category', None)
        if category_data:
            slug = category_data.get('slug') if isinstance(category_data, dict) else category_data
            try:
                category = Category.objects.get(slug=slug)
            except Category.DoesNotExist:
                # Fallback: auto-create for known registry-driven slugs to keep FE/BE in sync
                REGISTRY_SLUG_MAP = {
                    'attire-bridal': 'Bridal Attire',
                    'attire-groom': 'Groom Attire',
                    'attire-party': 'Wedding Party Attire',
                    'venue-hall': 'Venue Hall',
                    'venue-outdoor': 'Outdoor Venue',
                    'other-coming-soon': 'Other (Coming Soon)',
                }
                label = REGISTRY_SLUG_MAP.get(slug)
                if not label:
                    raise serializers.ValidationError({'category': 'Invalid category slug'})
                try:
                    with transaction.atomic():
                        category = Category.objects.create(name=label, slug=slug)
                except IntegrityError:
                    # Another process may have created it; retrieve
                    try:
                        category = Category.objects.get(slug=slug)
                    except Category.DoesNotExist:
                        raise serializers.ValidationError({'category': 'Invalid category slug'})
            validated_data['category'] = category
        # Ensure defaults for immutable provider-managed fields
        validated_data.setdefault('rating', 0)
        validated_data.setdefault('review_count', 0)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        # Prevent client from injecting publication status at creation
        validated_data.pop('status', None)
        validated_data.pop('published_at', None)
        return super().create(validated_data)

    def get_created_by(self, obj: Listing):
        if obj.created_by_id:
            return obj.created_by_id
        return None

    def get_provider_name(self, obj: Listing):
        # Prefer business name if available
        if obj.created_by and hasattr(obj.created_by, 'profile'):
            bn = getattr(obj.created_by.profile, 'business_name', None)
            if bn:
                return bn
        return obj.created_by.username if obj.created_by else None

    def get_provider_city(self, obj: Listing):
        if obj.created_by and hasattr(obj.created_by, 'profile'):
            return getattr(obj.created_by.profile, 'city', None)
        return None

    def get_provider_country(self, obj: Listing):
        if obj.created_by and hasattr(obj.created_by, 'profile'):
            return getattr(obj.created_by.profile, 'country', None)
        return None

    def to_representation(self, instance: Listing):
        data = super().to_representation(instance)
        # Re-map image to fully-qualified/normalized path like previous get_image implementation
        data['image'] = self._represent_image(instance)
        thumb = (instance.image_thumb or '').strip()
        if thumb:
            from django.conf import settings as dj_settings
            supabase_url = getattr(dj_settings, 'SUPABASE_URL', '')
            bucket = getattr(dj_settings, 'SUPABASE_BUCKET', '')
            backend = getattr(dj_settings, 'MEDIA_STORAGE_BACKEND', 'local')
            if backend in ('supabase','auto') and supabase_url and bucket and thumb.startswith('thumbs/'):
                data['image_thumb'] = f"{supabase_url}/storage/v1/object/public/{bucket}/{thumb}"  # For private bucket you may issue a fresh signed URL elsewhere
            else:
                data['image_thumb'] = thumb
        else:
            data['image_thumb'] = None
        return data


class ListingAvailabilitySerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ListingAvailability
        fields = [
            'id', 'listing', 'start_date', 'end_date', 'status', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'listing']

    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError('start_date must be <= end_date')
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)
