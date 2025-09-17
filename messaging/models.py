from django.db import models
from django.contrib.auth.models import User
from listings.models import Listing
from django.utils import timezone

class MessageThread(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='message_threads',
        null=True,
        blank=True,
    )
    # Use a through model to keep per-user state like unread counts
    participants = models.ManyToManyField(
        User,
        related_name='message_threads',
        through='ThreadParticipant',
        through_fields=('thread', 'user'),
    )
    last_updated = models.DateTimeField(auto_now=True)
    # Deprecated: kept for backwards compatibility; not used anymore
    unread_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Thread for {self.listing.title if self.listing else 'General Inquiry'}"

class Message(models.Model):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        tid = getattr(self.thread, 'pk', None)
        return f"Message from {self.sender.username} in thread {tid}"


class ThreadParticipant(models.Model):
    """Join model for participants with per-user state."""
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='thread_participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thread_participations')
    unread_count = models.PositiveIntegerField(default=0)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('thread', 'user')

    def mark_read(self):
        self.unread_count = 0
        self.last_read_at = timezone.now()
        self.save(update_fields=["unread_count", "last_read_at"])


class ContactRequest(models.Model):
    """A simple contact/request message initiated by a visitor from a listing page."""
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="contact_requests",
    )
    # Anonymous for now; we can associate to a user later when auth is added
    name = models.CharField(max_length=120)
    email_or_phone = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contact from {self.name} about {self.listing.title}"

