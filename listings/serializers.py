from rest_framework import serializers
from django.conf import settings
from .models import Category, Listing

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
        ]

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
