from django.contrib import admin
from .models import MessageThread, Message

admin.site.register(MessageThread)
admin.site.register(Message)

