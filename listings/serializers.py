from rest_framework import serializers
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
        url = obj.image or ''
        # If it looks like a backend-local assets path, leave it to frontend normalizer
        if url.startswith('assets/') or url.startswith('/assets/'):
            return url
        # If it's already an absolute URL, pass through
        if url.startswith('http://') or url.startswith('https://') or url.startswith('/src/assets/'):
            return url
        # Fallback to a known placeholder path the frontend can resolve
        return '/src/assets/luxury-wedding-hall.jpg'
