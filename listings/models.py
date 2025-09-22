from django.db import models
from django.conf import settings
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
    # For Supabase/private bucket: store relative path; serializer expands to public/signed URL.
    image = models.CharField(max_length=500)
    image_thumb = models.CharField(max_length=500, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.0'))
    review_count = models.PositiveIntegerField(default=0)
    # Allow empty location for drafts; enforce later if needed on publish
    location = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.CharField(max_length=100, blank=True, null=True) # Allow null for non-venue items
    price_range = models.CharField(max_length=100, blank=True)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    features = models.JSONField(default=list, blank=True)
    badges = models.JSONField(default=list, blank=True)
    featured = models.BooleanField(default=False)

    # Ownership & publication
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings', null=True, blank=True)
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=["status"], name="listing_status_idx"),
            models.Index(fields=["created_by"], name="listing_created_by_idx"),
        ]


class ListingAvailability(models.Model):
    STATUS_TENTATIVE = 'tentative'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = (
        (STATUS_TENTATIVE, 'Tentative'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELED, 'Canceled'),
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='availability')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_availability')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['listing', 'start_date']),
            models.Index(fields=['listing', 'end_date']),
        ]
        ordering = ['start_date']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date > self.end_date:
            raise ValidationError('start_date must be <= end_date')
        # Skip overlap validation if canceled
        if self.status == self.STATUS_CANCELED:
            return
        qs = ListingAvailability.objects.filter(
            listing=self.listing,
            status__in=[self.STATUS_TENTATIVE, self.STATUS_CONFIRMED],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError('Overlapping booking exists for this listing')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.listing_id} {self.start_date}→{self.end_date} ({self.status})"

