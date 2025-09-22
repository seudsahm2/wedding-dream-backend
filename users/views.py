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
		data["country"] = profile.country
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


class RegisterProviderV2View(APIView):
	"""Strict provider registration: requires business_name, business_phone, country, business_type."""
	permission_classes = []
	authentication_classes = []

	REQUIRED_FIELDS = ["username", "password", "business_name", "business_phone", "country", "business_type"]

	def post(self, request):
		payload = request.data.copy()
		missing = [f for f in self.REQUIRED_FIELDS if not str(payload.get(f, '')).strip()]
		if missing:
			return Response({"detail": "Missing required fields", "missing": missing}, status=400)
		# Basic country format check (ISO alpha-2)
		country = payload.get('country','').upper()
		if len(country) != 2:
			return Response({"country": ["Must be 2-letter ISO code"]}, status=400)
		payload['country'] = country
		# Validate provider service type existence if table migrated
		btype = payload.get('business_type')
		try:
			if not ProviderServiceType.objects.filter(slug=btype, active=True).exists():
				return Response({"business_type": ["Invalid provider type"]}, status=400)
		except Exception:
			pass
		# Create user via Django directly (avoids complexity of djoser remapping). Minimal fields only.
		username = payload['username']
		if User.objects.filter(username=username).exists():
			return Response({"username": ["Username already exists"]}, status=400)
		user = User.objects.create_user(username=username, password=payload['password'], email=payload.get('email') or '')
		profile, _ = UserProfile.objects.get_or_create(user=user)
		profile.role = UserProfile.ROLE_PROVIDER
		profile.business_name = payload['business_name']
		profile.business_phone = payload['business_phone']
		profile.business_type = btype
		profile.country = country
		profile.save()
		refresh = RefreshToken.for_user(user)
		data = UserSerializer(user).data
		data["role"] = profile.role
		data["is_provider"] = True
		data["access"] = str(refresh.access_token)
		data["refresh"] = str(refresh)
		data["country"] = profile.country
		return Response(data, status=201)


class ProviderUpgradeV2View(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		# Required fields for upgrade
		required = ["business_name", "business_phone", "business_type", "country"]
		missing = [f for f in required if not str(request.data.get(f, '')).strip()]
		if missing:
			return Response({"detail": "Missing required fields", "missing": missing}, status=400)
		country = request.data.get('country','').upper()
		if len(country) != 2:
			return Response({"country": ["Must be 2-letter ISO code"]}, status=400)
		btype = request.data.get('business_type')
		try:
			if not ProviderServiceType.objects.filter(slug=btype, active=True).exists():
				return Response({"business_type": ["Invalid provider type"]}, status=400)
		except Exception:
			pass
		profile.business_name = request.data['business_name']
		profile.business_phone = request.data['business_phone']
		profile.business_type = btype
		profile.country = country
		profile.role = UserProfile.ROLE_PROVIDER
		profile.save()
		ser = UserSerializer(request.user).data
		ser['role'] = profile.role
		ser['is_provider'] = True
		ser['country'] = profile.country
		return Response(ser, status=200)


class ProviderServiceTypeListView(generics.ListAPIView):
	queryset = ProviderServiceType.objects.filter(active=True)
	serializer_class = ProviderServiceTypeSerializer
	permission_classes = []
	pagination_class = None


class CountriesListView(APIView):
	permission_classes = []
	authentication_classes = []

	# Minimal initial set; can expand or load from a fixture later
	COUNTRIES = [
		{"code": "ET", "name": "Ethiopia"},
		{"code": "KE", "name": "Kenya"},
		{"code": "US", "name": "United States"},
		{"code": "GB", "name": "United Kingdom"},
		{"code": "AE", "name": "United Arab Emirates"},
	]

	def get(self, request):
		return Response(self.COUNTRIES)

