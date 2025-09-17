from django.contrib import admin
from .models import MessageThread, Message, ContactRequest

admin.site.register(MessageThread)
admin.site.register(Message)
admin.site.register(ContactRequest)

