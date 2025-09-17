from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import ContactRequest
from .serializers import ContactRequestSerializer, ContactRequestCreateSerializer


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

