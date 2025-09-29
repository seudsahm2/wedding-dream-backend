from django.db import models
from django.contrib.auth.models import User
from listings.models import Category

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    language = models.CharField(max_length=10, default='en')
    notifications = models.JSONField(default=dict)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_phone = models.CharField(max_length=40, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True, help_text='Optional business contact email (may differ from account email)')
    business_email_verified = models.BooleanField(default=False)
    country = models.CharField(max_length=2, blank=True, null=True, help_text='ISO 3166-1 alpha-2 country code')
    city = models.CharField(max_length=120, blank=True, null=True, help_text='City / locality name (frontend library sourced)')
    # User role: normal users can only view listings; providers can create/manage listings
    ROLE_NORMAL = 'normal'
    ROLE_PROVIDER = 'provider'
    ROLE_CHOICES = [
        (ROLE_NORMAL, 'Normal User'),
        (ROLE_PROVIDER, 'Provider'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_NORMAL, db_index=True)
    email_verified = models.BooleanField(default=False, help_text='True once user has confirmed email address')
    # New: Multi-select provider categories sourced from listings.Category (source of truth)
    provider_categories = models.ManyToManyField(Category, blank=True, related_name='profiles')
    # New: Persist provider subchoices as structured values and flattened tokens for search
    # Shape example: { "Gender": ["Men", "Women"], "Role": ["Stylist", "Makeup Artist"] }
    provider_subchoices = models.JSONField(default=dict, blank=True, null=True)
    # Flattened tokens like ["Gender:Men", "Role:Stylist"], for quick filtering/search later
    provider_subchoice_tokens = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.user.username


## Legacy ProviderServiceType model removed; categories are the single source of truth.

