from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import User, EmailChangeRequest


@shared_task
def example_task():  # existing placeholder pattern
    return "Users app task executed"


@shared_task(name="users.cleanup_unverified_and_email_changes")
def cleanup_unverified_and_email_changes():
    """Delete stale unverified user accounts & expired email change requests.

    Logic:
    - Unverified user (is_active=False) with no logins (last_login is null) older than UNVERIFIED_ACCOUNT_MAX_AGE_DAYS -> delete.
    - EmailChangeRequest cleanup:
        * Any request whose created_at older than EMAIL_CHANGE_REQUEST_RETENTION_DAYS -> delete.
        * Any expired (expires_at < now) request (consumed or not) -> delete (we don't keep them beyond usefulness).

    Settings used (with defaults if absent):
        UNVERIFIED_ACCOUNT_MAX_AGE_DAYS (default 14)
        EMAIL_CHANGE_REQUEST_RETENTION_DAYS (default 7)
    Returns counts for observability.
    """
    now = timezone.now()
    user_age_days = getattr(settings, "UNVERIFIED_ACCOUNT_MAX_AGE_DAYS", 14)
    retention_days = getattr(settings, "EMAIL_CHANGE_REQUEST_RETENTION_DAYS", 7)

    user_cutoff = now - timezone.timedelta(days=user_age_days)
    ecr_retention_cutoff = now - timezone.timedelta(days=retention_days)

    with transaction.atomic():
        # Unverified abandoned users
        abandoned_users_qs = User.objects.filter(
            is_active=False,
            last_login__isnull=True,
            date_joined__lt=user_cutoff,
        )
        deleted_users = abandoned_users_qs.count()
        if deleted_users:
            abandoned_users_qs.delete()

        # Email change requests: expired OR beyond retention
        ecr_qs = EmailChangeRequest.objects.filter(
            Q(expires_at__lt=now) | Q(created_at__lt=ecr_retention_cutoff)
        )
        deleted_ecr = ecr_qs.count()
        if deleted_ecr:
            ecr_qs.delete()

    return {"deleted_users": deleted_users, "deleted_email_change_requests": deleted_ecr}
