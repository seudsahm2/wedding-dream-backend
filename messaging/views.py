from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import ContactRequest, MessageThread, Message, ThreadParticipant
from .serializers import (
	ContactRequestSerializer,
	ContactRequestCreateSerializer,
	MessageThreadListSerializer,
	MessageThreadDetailSerializer,
	MessageCreateSerializer,
	MessageSerializer,
)
from django.db import transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from listings.models import Listing


class ContactRequestThrottle(SimpleRateThrottle):
	scope = "contact_requests"

	def get_cache_key(self, request, view):
		# Throttle by client IP for anonymous submissions
		ident = self.get_ident(request)
		return self.cache_format % {
			"scope": self.scope,
			"ident": ident,
		}


class ContactRequestCreateView(generics.CreateAPIView):
	queryset = ContactRequest.objects.all()
	serializer_class = ContactRequestCreateSerializer
	throttle_classes = [ContactRequestThrottle]

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		instance = serializer.save()
		out = ContactRequestSerializer(instance)
		headers = self.get_success_headers(out.data)
		return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)


class IsThreadParticipant(permissions.BasePermission):
	"""Allow access only to participants of the thread."""

	def has_object_permission(self, request, view, obj: MessageThread) -> bool:  # type: ignore[name-defined]
		if not request.user or not request.user.is_authenticated:
			return False
		return obj.participants.filter(id=request.user.id).exists()


class ThreadListView(generics.ListAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = MessageThreadListSerializer

	def get_queryset(self):
		user = self.request.user
		return (
			MessageThread.objects.filter(participants=user)
			.select_related("listing")
			.order_by("-last_updated")
		)

	def list(self, request, *args, **kwargs):
		qs = self.get_queryset()
		serializer = self.get_serializer(qs, many=True, context={"request": request})
		return Response(serializer.data)


class ThreadDetailView(generics.RetrieveAPIView):
	permission_classes = [permissions.IsAuthenticated, IsThreadParticipant]
	serializer_class = MessageThreadDetailSerializer
	lookup_field = "pk"

	def get_queryset(self):
		user = self.request.user
		return MessageThread.objects.filter(participants=user).select_related("listing")

	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		# Optional pagination for messages
		try:
			page = int(request.query_params.get("page", "0"))
			page_size = int(request.query_params.get("page_size", "0"))
		except ValueError:
			page = 0
			page_size = 0
		messages_qs = Message.objects.filter(thread=instance).order_by("created_at")
		total = messages_qs.count()
		if page > 0 and page_size > 0:
			start = (page - 1) * page_size
			end = start + page_size
			messages_qs = messages_qs[start:end]
		serializer = self.get_serializer(
			instance,
			context={"request": request, "messages_qs": messages_qs},
		)
		data = serializer.data
		if page > 0 and page_size > 0:
			data = {"count": total, "results": data}
		return Response(data)


class ThreadMessageCreateView(generics.CreateAPIView):
	permission_classes = [permissions.IsAuthenticated, IsThreadParticipant]
	serializer_class = MessageCreateSerializer

	def get_thread(self) -> MessageThread:
		thread = generics.get_object_or_404(MessageThread, pk=self.kwargs.get("pk"))
		# permission check via has_object_permission
		self.check_object_permissions(self.request, thread)
		return thread

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		thread = self.get_thread()
		with transaction.atomic():
			msg = Message.objects.create(
				thread=thread,
				sender=request.user,  # type: ignore[arg-type]
				text=serializer.validated_data["text"],
			)
			# Increment unread count for all other participants
			others = ThreadParticipant.objects.select_for_update().filter(thread=thread).exclude(user=request.user)
			for tp in others:
				tp.unread_count = (tp.unread_count or 0) + 1
				tp.save(update_fields=["unread_count"])
		out = MessageSerializer(msg, context={"request": request}).data
		return Response(out, status=status.HTTP_201_CREATED)


class ThreadMarkReadView(generics.UpdateAPIView):
	permission_classes = [permissions.IsAuthenticated, IsThreadParticipant]
	queryset = MessageThread.objects.all()
	lookup_field = "pk"

	def update(self, request, *args, **kwargs):
		thread = self.get_object()
		tp, _ = ThreadParticipant.objects.get_or_create(thread=thread, user=request.user)  # type: ignore[arg-type]
		tp.mark_read()
		return Response({"status": "ok", "unreadCount": 0})


class ThreadStartSerializer(MessageThreadDetailSerializer):
	class Meta(MessageThreadDetailSerializer.Meta):
		fields = MessageThreadDetailSerializer.Meta.fields


class ThreadStartView(generics.CreateAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = ThreadStartSerializer

	def create(self, request, *args, **kwargs):
		listing_id = request.data.get("listing_id")
		if not listing_id:
			return Response({"detail": "listing_id required"}, status=status.HTTP_400_BAD_REQUEST)
		listing = get_object_or_404(Listing, pk=listing_id)
		with transaction.atomic():
			# Find existing thread with this listing and current user (and provider, if modeled later)
			thread = (
				MessageThread.objects.select_for_update()
				.filter(listing=listing, participants=request.user)
				.first()
			)
			if not thread:
				thread = MessageThread.objects.create(listing=listing)
				# Add current user (through model auto-created)
				thread.participants.add(request.user)
			else:
				# Ensure ThreadParticipant exists for current user
				ThreadParticipant.objects.get_or_create(thread=thread, user=request.user)
		serializer = self.get_serializer(thread, context={"request": request, "messages_qs": Message.objects.none()})
		return Response(serializer.data, status=status.HTTP_201_CREATED)


class ThreadMessagesListView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated, IsThreadParticipant]
	serializer_class = MessageSerializer

	def get(self, request, *args, **kwargs):
		thread = get_object_or_404(MessageThread, pk=self.kwargs.get("pk"))
		self.check_object_permissions(request, thread)
		qs = Message.objects.filter(thread=thread).order_by("created_at")
		try:
			raw_page = request.query_params.get("page", "1")
			page_size = int(request.query_params.get("page_size", "20"))
		except ValueError:
			raw_page = "1"
			page_size = 20
		count = qs.count()
		num_pages = max(1, (count + page_size - 1) // page_size)
		if raw_page == "last":
			page = num_pages
		else:
			try:
				page = max(1, min(int(raw_page), num_pages))
			except ValueError:
				page = 1
		start = (page - 1) * page_size
		end = start + page_size
		items = list(qs[start:end])
		data = MessageSerializer(items, many=True, context={"request": request}).data
		return Response({
			"count": count,
			"page": page,
			"page_size": page_size,
			"num_pages": num_pages,
			"results": data,
		})

