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
    image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id',
            'title',
            'category',
            'type_label',
            'image',
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
        ]

    def get_image(self, obj: Listing):
        url = (obj.image or '').strip()
        # Already absolute or vite asset path
        if url.startswith('http://') or url.startswith('https://') or url.startswith('/src/assets/'):
            return url
        request = self.context.get('request')
        # Backend demo asset path -> absolute
        if url.startswith('assets/') or url.startswith('/assets/'):
            path = url.lstrip('/')
            abs_url = f"{settings.BACKEND_ASSETS_URL}{path.split('assets/', 1)[-1]}"
            if request:
                return request.build_absolute_uri(abs_url)
            return abs_url
        # If it's a relative media path, prefix MEDIA_URL
        if url:
            media_path = url.lstrip('/')
            abs_url = f"{settings.MEDIA_URL}{media_path}"
            if request:
                return request.build_absolute_uri(abs_url)
            return abs_url
        # Final fallback placeholder (frontend local asset)
        return '/src/assets/luxury-wedding-hall.jpg'
