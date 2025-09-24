from django.db import models
from django.contrib.auth.models import User
import secrets

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    language = models.CharField(max_length=10, default='en')
    notifications = models.JSONField(default=dict)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_phone = models.CharField(max_length=40, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
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


class EmailChangeRequest(models.Model):
    """Pending email change (verification required).

    Flow: user requests change -> token emailed to new address -> confirm consumes & applies.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_change_requests')
    new_email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):  # pragma: no cover
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def __str__(self):  # pragma: no cover
        return f"EmailChangeRequest<{self.user_id}:{self.new_email}>"


class UserSession(models.Model):
    """Represents a logical auth session (refresh token family instance).

    We store hashed identifiers & limited metadata for security review and revocation.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    # Short, URL-safe identifier for frontend reference (avoid exposing DB PK or hashes)
    def _new_public_id() -> str:
        # ~22 chars from 16 bytes urlsafe; trim to 22 for consistency
        return secrets.token_urlsafe(16)[:22]
    public_id = models.CharField(max_length=22, unique=True, db_index=True, default=_new_public_id)
    jti_hash = models.CharField(max_length=64, db_index=True)  # SHA256 of refresh token JTI
    user_agent = models.CharField(max_length=300, blank=True)
    ua_hash = models.CharField(max_length=64, blank=True)  # SHA256 of normalized UA for grouping
    ip_hash = models.CharField(max_length=64, blank=True)  # SHA256 of salted IP
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    label = models.CharField(max_length=120, blank=True)  # derived device label for UX

    class Meta:
        indexes = [
            models.Index(fields=["user", "last_seen"]),
            models.Index(fields=["jti_hash"]),
            models.Index(fields=["user", "revoked_at"]),
        ]
        ordering = ["-last_seen"]

    def mark_revoked(self):  # pragma: no cover
        from django.utils import timezone
        if not self.revoked_at:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def is_active(self):  # pragma: no cover
        return self.revoked_at is None

    def __str__(self):  # pragma: no cover
        return f"UserSession<{self.user_id}:{self.jti_hash[:8]}>"

