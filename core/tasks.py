from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def send_test_email(self, to_email: str) -> str:
    subject = "Test email from Wedding Dream"
    message = "Hello! This is a test email sent by Celery."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
    send_mail(subject, message, from_email, [to_email], fail_silently=False)
    return "sent"


@shared_task(bind=True)
def cleanup_temp_files(self) -> str:
    # Placeholder for background cleanup routines
    return "ok"
