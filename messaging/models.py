from django.db import models
from django.contrib.auth.models import User
from listings.models import Listing

class MessageThread(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True)
    participants = models.ManyToManyField(User, related_name='message_threads')
    last_updated = models.DateTimeField(auto_now=True)
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
        return f"Message from {self.sender.username} in thread {self.thread.id}"

