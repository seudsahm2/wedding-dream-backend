from rest_framework import permissions, generics
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile
from .serializers import UserSerializer, UserProfileSerializer


class MeView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		# Ensure profile exists
		UserProfile.objects.get_or_create(user=request.user)
		serializer = UserSerializer(request.user)
		return Response(serializer.data)


class PreferencesView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def put(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		serializer = UserProfileSerializer(instance=profile, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)

