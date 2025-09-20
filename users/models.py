from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    language = models.CharField(max_length=10, default='en')
    notifications = models.JSONField(default=dict)
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

