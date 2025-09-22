from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from django.conf import settings

try:
    from djoser.signals import user_activated  # type: ignore
except Exception:  # pragma: no cover
    user_activated = None  # type: ignore


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


if user_activated:
    @receiver(user_activated)  # type: ignore[misc]
    def mark_email_verified(sender, user: User, **kwargs):  # type: ignore[override]
        try:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.email_verified:
                profile.email_verified = True
                profile.save(update_fields=["email_verified"])
        except Exception:
            pass
