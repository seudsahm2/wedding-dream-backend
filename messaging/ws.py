from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import MessageThread, Message, ThreadParticipant


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.thread_pk = self.scope['url_route']['kwargs'].get('pk')
        self.group_name = f"thread_{self.thread_pk}"

        user = self.scope.get('user')
        if isinstance(user, AnonymousUser) or not await self._is_participant(self.thread_pk, user.id):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Expect { type: 'message', text: '...' }
        if content.get('type') != 'message':
            return
        text = (content.get('text') or '').strip()
        if not text:
            return
        user = self.scope.get('user')
        msg = await self._create_message(self.thread_pk, user.id, text)
        payload = {
            'event': 'message',
            'data': {
                'id': msg['id'],
                'thread_id': msg['thread_id'],
                'sender': 'me' if msg['sender_id'] == user.id else 'provider',
                'text': msg['text'],
                'createdAt': msg['created_at'],
            }
        }
        await self.channel_layer.group_send(self.group_name, { 'type': 'broadcast.message', 'payload': payload })

    async def broadcast_message(self, event):
        await self.send_json(event['payload'])

    # --- helpers ---
    @database_sync_to_async
    def _is_participant(self, thread_pk: int, user_id: int) -> bool:
        try:
            thread = MessageThread.objects.get(pk=thread_pk)
        except MessageThread.DoesNotExist:
            return False
        return thread.participants.filter(pk=user_id).exists()

    @database_sync_to_async
    def _create_message(self, thread_pk: int, user_id: int, text: str):
        thread = MessageThread.objects.get(pk=thread_pk)
        msg = Message.objects.create(thread=thread, sender_id=user_id, text=text)
        # increment unread for others
        others = ThreadParticipant.objects.filter(thread=thread).exclude(user_id=user_id)
        for tp in others:
            tp.unread_count = (tp.unread_count or 0) + 1
            tp.save(update_fields=["unread_count"])
        return {
            'id': msg.id,
            'thread_id': msg.thread_id,
            'sender_id': msg.sender_id,
            'text': msg.text,
            'created_at': msg.created_at.isoformat(),
        }
