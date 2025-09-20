from rest_framework import permissions, generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, ProviderServiceType
from core.throttling import PreferencesUpdateThrottle
from .serializers import (
	UserSerializer,
	UserProfileSerializer,
	ProviderUpgradeSerializer,
	ProviderServiceTypeSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from djoser.views import UserViewSet
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory


class MeView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		# Ensure profile exists
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		serializer = UserSerializer(request.user)
		data = serializer.data
		data["role"] = profile.role
		data["is_provider"] = profile.role == UserProfile.ROLE_PROVIDER
		return Response(data)


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
		update_fields = []
		if profile.role != UserProfile.ROLE_PROVIDER:
			profile.role = UserProfile.ROLE_PROVIDER
			update_fields.append("role")
		# Allow optional business fields on upgrade
		for fld in ["business_name", "business_phone", "business_type"]:
			val = request.data.get(fld)
			if val is not None:
				setattr(profile, fld, val)
				if fld not in update_fields:
					update_fields.append(fld)
		if update_fields:
			profile.save(update_fields=update_fields)
		return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class RegisterProviderView(APIView):
	"""Register a brand new provider (non-authenticated). Returns user + JWT tokens.
	This wraps Djoser's create user, then marks profile role=provider and persists optional business fields.
	"""
	permission_classes = []
	authentication_classes = []

	def post(self, request):
		"""Create a new provider user.
		Avoid RawPostDataException by reading request.data ONCE and rebuilding a fresh DRF request for Djoser.
		"""
		incoming_payload = request.data.copy()  # safe copy; forces parse once
		# Build a new request object for Djoser's ViewSet to prevent double stream read
		factory = APIRequestFactory()
		raw_req = factory.post(
			"/auth/register", data=incoming_payload, format="json"
		)
		# Propagate headers (e.g., request id) if needed
		for hdr, val in request.headers.items():
			if hdr.lower().startswith("x-"):
				raw_req.META["HTTP_" + hdr.upper().replace('-', '_')] = val
		# Call Djoser create
		view = UserViewSet.as_view({"post": "create"})
		create_resp = view(raw_req)
		if create_resp.status_code not in (200, 201):
			return create_resp
		username = incoming_payload.get("username")
		try:
			user = User.objects.get(username=username)
		except User.DoesNotExist:
			return Response({"detail": "User creation inconsistency"}, status=500)
		profile, _ = UserProfile.objects.get_or_create(user=user)
		profile.role = UserProfile.ROLE_PROVIDER
		for fld in ["business_name", "business_phone", "business_type"]:
			val = incoming_payload.get(fld)
			if val:
				setattr(profile, fld, val)
		# Validate business_type if provided
		bt = getattr(profile, "business_type", None)
		if bt:
			from django.db import OperationalError, ProgrammingError
			try:
				if not ProviderServiceType.objects.filter(slug=bt, active=True).exists():
					return Response({"business_type": ["Invalid or inactive provider type"]}, status=400)
			except (OperationalError, ProgrammingError):
				# Table likely not migrated yet; continue without blocking user creation
				pass
		profile.save()

		# Issue JWT tokens once (outside loop)
		refresh = RefreshToken.for_user(user)
		data = UserSerializer(user).data
		data["access"] = str(refresh.access_token)
		data["refresh"] = str(refresh)
		return Response(data, status=status.HTTP_201_CREATED)


class ProviderServiceTypeListView(generics.ListAPIView):
	queryset = ProviderServiceType.objects.filter(active=True)
	serializer_class = ProviderServiceTypeSerializer
	permission_classes = []
	pagination_class = None

