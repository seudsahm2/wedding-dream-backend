from django.db import models
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Listing(models.Model):
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='listings')
    type_label = models.CharField(max_length=100, blank=True)
    image = models.URLField(max_length=500)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.0'))
    review_count = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=255)
    capacity = models.CharField(max_length=100, blank=True, null=True) # Allow null for non-venue items
    price_range = models.CharField(max_length=100, blank=True)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    features = models.JSONField(default=list, blank=True)
    badges = models.JSONField(default=list, blank=True)
    featured = models.BooleanField(default=False)

    # Category-specific attributes, allowing them to be optional
    venue_attrs = models.JSONField(default=dict, blank=True, null=True)
    attire_attrs = models.JSONField(default=dict, blank=True, null=True)
    catering_attrs = models.JSONField(default=dict, blank=True, null=True)
    rental_attrs = models.JSONField(default=dict, blank=True, null=True)
    service_attrs = models.JSONField(default=dict, blank=True, null=True) # Renamed from specialty_attrs
    accessory_attrs = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["-featured", "-rating"], name="listing_featured_rating_idx"),
            models.Index(fields=["rating"], name="listing_rating_idx"),
            models.Index(fields=["price_min"], name="listing_price_min_idx"),
            models.Index(fields=["category", "featured"], name="listing_category_featured_idx"),
        ]

