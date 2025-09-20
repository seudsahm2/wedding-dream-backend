from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    language = models.CharField(max_length=10, default='en')
    notifications = models.JSONField(default=dict)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_phone = models.CharField(max_length=40, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    # User role: normal users can only view listings; providers can create/manage listings
    ROLE_NORMAL = 'normal'
    ROLE_PROVIDER = 'provider'
    ROLE_CHOICES = [
        (ROLE_NORMAL, 'Normal User'),
        (ROLE_PROVIDER, 'Provider'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_NORMAL, db_index=True)

    def __str__(self):
        return self.user.username


class ProviderServiceType(models.Model):
    """Represents a selectable business/provider type (e.g., bridal attire, venue)."""
    slug = models.SlugField(primary_key=True, max_length=60)
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):  # pragma: no cover
        return self.name

