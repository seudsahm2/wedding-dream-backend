from rest_framework import permissions, generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile
from core.throttling import PreferencesUpdateThrottle
from .serializers import UserSerializer, UserProfileSerializer, ProviderUpgradeSerializer


class MeView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		# Ensure profile exists
		UserProfile.objects.get_or_create(user=request.user)
		serializer = UserSerializer(request.user)
		return Response(serializer.data)


class PreferencesView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [PreferencesUpdateThrottle]

	def put(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		serializer = UserProfileSerializer(instance=profile, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)


class ProviderUpgradeView(generics.GenericAPIView):
	"""Allow an authenticated normal user to become a provider.
	Idempotent: calling again when already provider just returns current profile.
	"""
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = ProviderUpgradeSerializer

	def post(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		if profile.role != UserProfile.ROLE_PROVIDER:
			profile.role = UserProfile.ROLE_PROVIDER
			profile.save(update_fields=["role"])
		return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

